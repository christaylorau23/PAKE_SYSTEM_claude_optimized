"""InvestmentMapper - Maps trends to specific investment opportunities

Converts trend analysis into actionable investment recommendations with specific symbols and strategies.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..models.investment_opportunity import (
    ActionType,
    InvestmentOpportunity,
    InvestmentVehicle,
    RiskLevel,
)
from ..models.trend_correlation import TrendCorrelation
from ..models.trend_signal import TrendSignal
from .trend_analyzer import TrendAnalysisResult


@dataclass
class InvestmentMapping:
    """Mapping between trend and investment vehicle"""

    keyword_pattern: str
    investment_vehicles: list[InvestmentVehicle]
    symbols: list[str]
    sector: str
    confidence_multiplier: float = 1.0


class InvestmentMapper:
    """Advanced investment opportunity mapping engine

    Capabilities:
    - Trend-to-investment mapping
    - Symbol recommendation
    - Risk assessment
    - Position sizing
    - Entry/exit timing
    - Portfolio integration
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Investment mapping database
        self.investment_mappings = self._initialize_mappings()

        # Market data and symbols database (would integrate with real data in
        # production)
        self.symbol_database = self._initialize_symbol_database()

        # Risk parameters
        self.max_position_size = 10.0  # Maximum 10% position size
        self.default_stop_loss = 15.0  # 15% stop loss

        # Performance tracking
        self.generated_opportunities = []

    def _initialize_mappings(self) -> list[InvestmentMapping]:
        """Initialize trend-to-investment mappings"""
        return [
            # Technology trends
            InvestmentMapping(
                keyword_pattern="artificial intelligence|AI|machine learning|chatgpt|openai",
                investment_vehicles=[InvestmentVehicle.STOCKS, InvestmentVehicle.ETF],
                symbols=[
                    "NVDA",
                    "MSFT",
                    "GOOGL",
                    "TSLA",
                    "PLTR",
                    "ROBO",
                    "BOTZ",
                    "ARKQ",
                ],
                sector="Technology",
                confidence_multiplier=1.2,
            ),
            InvestmentMapping(
                keyword_pattern="cryptocurrency|bitcoin|ethereum|crypto|blockchain",
                investment_vehicles=[InvestmentVehicle.CRYPTO, InvestmentVehicle.ETF],
                symbols=["BTC-USD", "ETH-USD", "COIN", "MSTR", "BITO", "ETHE"],
                sector="Cryptocurrency",
                confidence_multiplier=0.8,
            ),
            InvestmentMapping(
                keyword_pattern="electric vehicle|EV|tesla|rivian|lucid",
                investment_vehicles=[InvestmentVehicle.STOCKS, InvestmentVehicle.ETF],
                symbols=["TSLA", "RIVN", "LCID", "NIO", "XPEV", "DRIV", "IDRV"],
                sector="Automotive",
                confidence_multiplier=1.1,
            ),
            InvestmentMapping(
                keyword_pattern="renewable energy|solar|wind|clean energy",
                investment_vehicles=[InvestmentVehicle.STOCKS, InvestmentVehicle.ETF],
                symbols=["ENPH", "SEDG", "NEE", "ICLN", "PBW", "QCLN"],
                sector="Energy",
                confidence_multiplier=1.0,
            ),
            InvestmentMapping(
                keyword_pattern="healthcare|biotech|pharma|medicine",
                investment_vehicles=[InvestmentVehicle.STOCKS, InvestmentVehicle.ETF],
                symbols=["JNJ", "PFE", "MRNA", "ABBV", "XBI", "IBB", "VHT"],
                sector="Healthcare",
                confidence_multiplier=0.9,
            ),
            InvestmentMapping(
                keyword_pattern="gaming|esports|metaverse|virtual reality",
                investment_vehicles=[InvestmentVehicle.STOCKS, InvestmentVehicle.ETF],
                symbols=["NVDA", "RBLX", "TTWO", "ATVI", "EA", "HERO", "ESPO"],
                sector="Gaming",
                confidence_multiplier=1.0,
            ),
            InvestmentMapping(
                keyword_pattern="cloud computing|AWS|azure|software",
                investment_vehicles=[InvestmentVehicle.STOCKS, InvestmentVehicle.ETF],
                symbols=["AMZN", "MSFT", "CRM", "SNOW", "PLTR", "SKYY", "WCLD"],
                sector="Cloud Computing",
                confidence_multiplier=1.1,
            ),
            InvestmentMapping(
                keyword_pattern="space|spacex|satellite|aerospace",
                investment_vehicles=[InvestmentVehicle.STOCKS, InvestmentVehicle.ETF],
                symbols=["LMT", "BA", "RTX", "NOC", "ARKX", "UFO"],
                sector="Aerospace",
                confidence_multiplier=0.8,
            ),
            InvestmentMapping(
                keyword_pattern="food delivery|restaurant|dining",
                investment_vehicles=[InvestmentVehicle.STOCKS],
                symbols=["UBER", "DASH", "MCD", "SBUX", "CMG"],
                sector="Consumer Services",
                confidence_multiplier=0.9,
            ),
            InvestmentMapping(
                keyword_pattern="streaming|netflix|disney|entertainment",
                investment_vehicles=[InvestmentVehicle.STOCKS],
                symbols=["NFLX", "DIS", "WBD", "PARA", "ROKU"],
                sector="Entertainment",
                confidence_multiplier=0.8,
            ),
        ]

    def _initialize_symbol_database(self) -> dict[str, dict[str, Any]]:
        """Initialize symbol database with market data"""
        # This would be populated from real market data APIs
        return {
            "NVDA": {
                "name": "NVIDIA Corporation",
                "sector": "Technology",
                "market_cap": 1500000000000,  # $1.5T
                "volatility": 0.35,
                "beta": 1.6,
                "dividend_yield": 0.01,
            },
            "TSLA": {
                "name": "Tesla Inc",
                "sector": "Automotive",
                "market_cap": 800000000000,  # $800B
                "volatility": 0.45,
                "beta": 2.1,
                "dividend_yield": 0.0,
            },
            "BTC-USD": {
                "name": "Bitcoin",
                "sector": "Cryptocurrency",
                "market_cap": 600000000000,  # $600B
                "volatility": 0.65,
                "beta": 1.0,
                "dividend_yield": 0.0,
            },
            # Add more symbols as needed
        }

    async def map_trends_to_opportunities(
        self,
        analysis_results: list[TrendAnalysisResult],
        correlations: list[TrendCorrelation] = None,
    ) -> list[InvestmentOpportunity]:
        """Map trend analysis results to investment opportunities

        Args:
            analysis_results: Results from trend analysis
            correlations: Optional trend correlations for enhanced mapping

        Returns:
            List of investment opportunities
        """
        opportunities = []
        correlations = correlations or []

        for analysis in analysis_results:
            # Find matching investment mappings
            matching_mappings = self._find_matching_mappings(
                analysis.trend_signal.keyword,
            )

            for mapping in matching_mappings:
                # Create investment opportunity for each mapping
                opportunity = await self._create_investment_opportunity(
                    analysis,
                    mapping,
                    correlations,
                )

                if opportunity:
                    opportunities.append(opportunity)
                    self.generated_opportunities.append(opportunity)

        # Sort by investment score (highest first)
        opportunities.sort(key=lambda x: x.confidence_score, reverse=True)

        self.logger.info(
            f"Generated {len(opportunities)} investment opportunities from {
                len(analysis_results)
            } trends",
        )

        return opportunities

    def _find_matching_mappings(self, keyword: str) -> list[InvestmentMapping]:
        """Find investment mappings that match the trend keyword"""
        import re

        matching = []

        for mapping in self.investment_mappings:
            # Use regex to match patterns
            pattern = mapping.keyword_pattern.lower()
            if re.search(pattern, keyword.lower()):
                matching.append(mapping)

        return matching

    async def _create_investment_opportunity(
        self,
        analysis: TrendAnalysisResult,
        mapping: InvestmentMapping,
        correlations: list[TrendCorrelation],
    ) -> InvestmentOpportunity | None:
        """Create investment opportunity from trend analysis and mapping"""
        trend = analysis.trend_signal

        # Determine primary investment vehicle
        primary_vehicle = mapping.investment_vehicles[0]

        # Select best symbols for this trend
        selected_symbols = self._select_best_symbols(mapping.symbols, trend, analysis)

        # Calculate confidence score
        base_confidence = analysis.investment_score * mapping.confidence_multiplier
        confidence_score = min(1.0, base_confidence)

        # Determine action type
        action = self._determine_action_type(analysis, confidence_score)

        # Assess risk level
        risk_level = self._assess_risk_level(analysis, mapping, primary_vehicle)

        # Calculate expected return
        expected_return = self._calculate_expected_return(analysis, mapping, risk_level)

        # Determine time horizon
        time_horizon = self._calculate_time_horizon(analysis)

        # Calculate position sizing
        position_size = self._calculate_position_size(
            confidence_score,
            risk_level,
            expected_return,
        )

        # Set stop loss
        stop_loss = self._calculate_stop_loss(risk_level, primary_vehicle)

        # Generate reasoning
        reasoning = self._generate_investment_reasoning(trend, analysis, mapping)

        # Find relevant correlations
        relevant_correlations = [
            corr
            for corr in correlations
            if corr.primary_trend.keyword == trend.keyword
            or corr.secondary_trend.keyword == trend.keyword
        ]

        try:
            opportunity = InvestmentOpportunity(
                trend_signal=trend,
                correlations=relevant_correlations[:3],  # Limit to top 3 correlations
                investment_vehicle=primary_vehicle,
                recommended_action=action,
                confidence_score=confidence_score,
                risk_level=risk_level,
                expected_return_pct=expected_return,
                time_horizon_days=time_horizon,
                entry_price_target=None,  # Would be populated with real market data
                exit_price_target=None,  # Would be populated with real market data
                stop_loss_pct=stop_loss,
                position_size_pct=position_size,
                symbols=selected_symbols,
                reasoning=reasoning,
                timestamp=datetime.now(),
            )

            return opportunity

        except Exception as e:
            self.logger.error(f"Error creating investment opportunity: {e}")
            return None

    def _select_best_symbols(
        self,
        candidate_symbols: list[str],
        trend: TrendSignal,
        analysis: TrendAnalysisResult,
    ) -> list[str]:
        """Select the best symbols based on trend characteristics"""
        # Score each symbol
        symbol_scores = []

        for symbol in candidate_symbols:
            symbol_data = self.symbol_database.get(symbol, {})

            # Base score from trend strength
            score = trend.trend_strength

            # Adjust for volatility match
            symbol_volatility = symbol_data.get("volatility", 0.3)
            if trend.momentum > 0.8:
                # High momentum trends prefer higher volatility
                score += symbol_volatility * 0.2
            else:
                # Lower momentum trends prefer stability
                score += (1.0 - symbol_volatility) * 0.2

            # Beta adjustment
            beta = symbol_data.get("beta", 1.0)
            if analysis.predicted_lifecycle_stage.value == "emerging":
                # Emerging trends prefer higher beta
                score += min(beta / 2.0, 0.3)

            symbol_scores.append((symbol, score))

        # Sort by score and return top symbols
        symbol_scores.sort(key=lambda x: x[1], reverse=True)

        # Return top 3 symbols
        return [symbol for symbol, _ in symbol_scores[:3]]

    def _determine_action_type(
        self,
        analysis: TrendAnalysisResult,
        confidence: float,
    ) -> ActionType:
        """Determine recommended action based on analysis"""
        if confidence < 0.3:
            return ActionType.AVOID
        if confidence < 0.5:
            return ActionType.WATCH
        if confidence < 0.7:
            if analysis.predicted_lifecycle_stage.value in ["emerging", "growing"]:
                return ActionType.BUY
            return ActionType.HOLD
        if analysis.predicted_lifecycle_stage.value in ["declining", "dormant"]:
            return ActionType.SELL
        return ActionType.BUY

    def _assess_risk_level(
        self,
        analysis: TrendAnalysisResult,
        mapping: InvestmentMapping,
        vehicle: InvestmentVehicle,
    ) -> RiskLevel:
        """Assess risk level for the investment"""
        # Base risk from trend analysis
        overall_risk = analysis.risk_assessment.get("overall_risk", 0.5)

        # Vehicle risk adjustment
        vehicle_risk_multipliers = {
            InvestmentVehicle.STOCKS: 1.0,
            InvestmentVehicle.ETF: 0.8,
            InvestmentVehicle.CRYPTO: 1.5,
            InvestmentVehicle.OPTIONS: 1.8,
            InvestmentVehicle.FUTURES: 1.6,
            InvestmentVehicle.COMMODITIES: 1.2,
            InvestmentVehicle.FOREX: 1.3,
        }

        adjusted_risk = overall_risk * vehicle_risk_multipliers.get(vehicle, 1.0)

        # Lifecycle stage risk
        stage_risk = {
            "emerging": 0.3,
            "growing": 0.2,
            "peak": 0.5,
            "declining": 0.7,
            "dormant": 0.9,
        }

        lifecycle_risk = stage_risk.get(analysis.predicted_lifecycle_stage.value, 0.5)

        # Combined risk
        final_risk = (adjusted_risk * 0.6) + (lifecycle_risk * 0.4)

        if final_risk < 0.3:
            return RiskLevel.LOW
        if final_risk < 0.6:
            return RiskLevel.MODERATE
        if final_risk < 0.8:
            return RiskLevel.HIGH
        return RiskLevel.VERY_HIGH

    def _calculate_expected_return(
        self,
        analysis: TrendAnalysisResult,
        mapping: InvestmentMapping,
        risk_level: RiskLevel,
    ) -> float:
        """Calculate expected return percentage"""
        # Base return from investment score
        base_return = analysis.investment_score * 20.0  # Up to 20% return

        # Risk-return adjustment
        risk_multipliers = {
            RiskLevel.LOW: 0.6,
            RiskLevel.MODERATE: 1.0,
            RiskLevel.HIGH: 1.4,
            RiskLevel.VERY_HIGH: 1.8,
        }

        risk_adjusted_return = base_return * risk_multipliers[risk_level]

        # Lifecycle stage adjustment
        stage_multipliers = {
            "emerging": 1.5,
            "growing": 1.2,
            "peak": 0.8,
            "declining": 0.4,
            "dormant": 0.2,
        }

        stage_multiplier = stage_multipliers.get(
            analysis.predicted_lifecycle_stage.value,
            1.0,
        )

        final_return = risk_adjusted_return * stage_multiplier

        # Cap returns at reasonable levels
        return max(-50.0, min(100.0, final_return))

    def _calculate_time_horizon(self, analysis: TrendAnalysisResult) -> int:
        """Calculate investment time horizon in days"""
        # Base horizon from lifecycle stage
        stage_horizons = {
            "emerging": 30,  # 1 month
            "growing": 60,  # 2 months
            "peak": 14,  # 2 weeks
            "declining": 7,  # 1 week
            "dormant": 3,  # 3 days
        }

        base_horizon = stage_horizons.get(analysis.predicted_lifecycle_stage.value, 30)

        # Adjust based on momentum trajectory
        if len(analysis.momentum_trajectory) >= 3:
            momentum_trend = (
                analysis.momentum_trajectory[-1] - analysis.momentum_trajectory[-3]
            )
            if momentum_trend > 0.1:
                # Growing momentum - extend horizon
                base_horizon = int(base_horizon * 1.5)
            elif momentum_trend < -0.1:
                # Declining momentum - shorten horizon
                base_horizon = int(base_horizon * 0.7)

        return max(1, min(365, base_horizon))

    def _calculate_position_size(
        self,
        confidence: float,
        risk_level: RiskLevel,
        expected_return: float,
    ) -> float:
        """Calculate recommended position size percentage"""
        # Base size from confidence
        base_size = confidence * self.max_position_size

        # Risk adjustment
        risk_adjustments = {
            RiskLevel.LOW: 1.0,
            RiskLevel.MODERATE: 0.8,
            RiskLevel.HIGH: 0.6,
            RiskLevel.VERY_HIGH: 0.4,
        }

        risk_adjusted_size = base_size * risk_adjustments[risk_level]

        # Return adjustment (lower position for negative expected returns)
        if expected_return < 0:
            risk_adjusted_size *= 0.3
        elif expected_return < 5:
            risk_adjusted_size *= 0.7

        return max(0.1, min(self.max_position_size, risk_adjusted_size))

    def _calculate_stop_loss(
        self,
        risk_level: RiskLevel,
        vehicle: InvestmentVehicle,
    ) -> float:
        """Calculate stop loss percentage"""
        # Base stop loss by risk level
        base_stop_loss = {
            RiskLevel.LOW: 8.0,
            RiskLevel.MODERATE: 12.0,
            RiskLevel.HIGH: 18.0,
            RiskLevel.VERY_HIGH: 25.0,
        }

        stop_loss = base_stop_loss[risk_level]

        # Vehicle adjustment
        vehicle_adjustments = {
            InvestmentVehicle.CRYPTO: 1.5,
            InvestmentVehicle.OPTIONS: 1.8,
            InvestmentVehicle.FUTURES: 1.6,
            InvestmentVehicle.STOCKS: 1.0,
            InvestmentVehicle.ETF: 0.9,
            InvestmentVehicle.COMMODITIES: 1.2,
            InvestmentVehicle.FOREX: 1.3,
        }

        adjusted_stop_loss = stop_loss * vehicle_adjustments.get(vehicle, 1.0)

        return max(5.0, min(50.0, adjusted_stop_loss))

    def _generate_investment_reasoning(
        self,
        trend: TrendSignal,
        analysis: TrendAnalysisResult,
        mapping: InvestmentMapping,
    ) -> str:
        """Generate human-readable investment reasoning"""
        reasoning_parts = []

        # Trend strength
        if trend.trend_strength > 0.8:
            reasoning_parts.append(
                f"Strong {mapping.sector} trend '{trend.keyword}' with {
                    trend.trend_strength:.1%} strength",
            )
        else:
            reasoning_parts.append(
                f"Moderate {mapping.sector} trend '{trend.keyword}' detected",
            )

        # Lifecycle stage
        reasoning_parts.append(
            f"Currently in {analysis.predicted_lifecycle_stage.value} stage",
        )

        # Investment score
        if analysis.investment_score > 0.7:
            reasoning_parts.append(
                "High investment potential based on momentum and growth metrics",
            )
        elif analysis.investment_score > 0.5:
            reasoning_parts.append(
                "Moderate investment potential with favorable trend characteristics",
            )
        else:
            reasoning_parts.append(
                "Limited investment potential requiring careful monitoring",
            )

        # Volume growth
        if analysis.volume_growth_rate > 0.2:
            reasoning_parts.append(
                f"Strong volume growth of {analysis.volume_growth_rate:.1%}",
            )

        # Platform source
        reasoning_parts.append(f"Trend identified on {trend.platform.value}")

        return ". ".join(reasoning_parts) + "."

    async def get_portfolio_recommendations(
        self,
        opportunities: list[InvestmentOpportunity],
        max_positions: int = 10,
        max_sector_exposure: float = 0.3,
    ) -> list[InvestmentOpportunity]:
        """Get portfolio-optimized investment recommendations"""
        if not opportunities:
            return []

        # Group by sector
        sector_opportunities = {}
        for opp in opportunities:
            # Find mapping to get sector
            for mapping in self.investment_mappings:
                if any(symbol in opp.symbols for symbol in mapping.symbols):
                    sector = mapping.sector
                    if sector not in sector_opportunities:
                        sector_opportunities[sector] = []
                    sector_opportunities[sector].append(opp)
                    break

        # Select diversified portfolio
        selected = []
        total_position_size = 0.0
        sector_exposures = {}

        # Sort all opportunities by confidence score
        sorted_opportunities = sorted(
            opportunities,
            key=lambda x: x.confidence_score,
            reverse=True,
        )

        for opp in sorted_opportunities:
            if len(selected) >= max_positions:
                break

            # Find sector for this opportunity
            opp_sector = "Unknown"
            for mapping in self.investment_mappings:
                if any(symbol in opp.symbols for symbol in mapping.symbols):
                    opp_sector = mapping.sector
                    break

            # Check sector exposure limits
            current_sector_exposure = sector_exposures.get(opp_sector, 0.0)
            if (
                current_sector_exposure + opp.position_size_pct
                > max_sector_exposure * 100
            ):
                continue

            # Check total position size
            if total_position_size + opp.position_size_pct > 100.0:
                continue

            # Add to portfolio
            selected.append(opp)
            total_position_size += opp.position_size_pct
            sector_exposures[opp_sector] = (
                current_sector_exposure + opp.position_size_pct
            )

        self.logger.info(
            f"Selected {len(selected)} opportunities for diversified portfolio",
        )
        return selected

    def get_mapping_statistics(self) -> dict[str, Any]:
        """Get statistics about investment mappings"""
        total_symbols = sum(
            len(mapping.symbols) for mapping in self.investment_mappings
        )
        sectors = set(mapping.sector for mapping in self.investment_mappings)

        return {
            "total_mappings": len(self.investment_mappings),
            "total_symbols": total_symbols,
            "sectors_covered": len(sectors),
            "sector_list": list(sectors),
            "opportunities_generated": len(self.generated_opportunities),
            "average_symbols_per_mapping": total_symbols
            / len(self.investment_mappings),
        }
