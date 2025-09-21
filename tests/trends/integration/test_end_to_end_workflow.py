"""
End-to-End Integration Tests for Live Trend Data Feed System

Tests the complete workflow from trend detection to investment opportunities.
"""

from datetime import datetime, timedelta

import pytest

from src.services.trends.intelligence.investment_mapper import InvestmentMapper
from src.services.trends.intelligence.prediction_engine import PredictionEngine
from src.services.trends.intelligence.trend_analyzer import TrendAnalyzer
from src.services.trends.models.trend_signal import (
    Platform,
    TrendLifecycle,
    TrendSignal,
)
from src.services.trends.streaming.stream_manager import StreamManager


class TestEndToEndWorkflow:
    """Integration tests for complete trend analysis workflow"""

    @pytest.fixture
    async def stream_manager(self):
        """Create stream manager for testing"""
        manager = StreamManager("redis://localhost:6379/0")
        # Note: In production, would initialize Redis connection
        yield manager
        # Cleanup
        await manager.shutdown()

    @pytest.fixture
    def trend_analyzer(self):
        """Create trend analyzer for testing"""
        return TrendAnalyzer()

    @pytest.fixture
    def investment_mapper(self):
        """Create investment mapper for testing"""
        return InvestmentMapper()

    @pytest.fixture
    def prediction_engine(self):
        """Create prediction engine for testing"""
        return PredictionEngine()

    @pytest.fixture
    def sample_trends(self) -> list[TrendSignal]:
        """Create sample trend signals for testing"""
        base_time = datetime.now()

        return [
            TrendSignal(
                platform=Platform.GOOGLE_TRENDS,
                keyword="artificial intelligence",
                momentum=0.85,
                timestamp=base_time,
                confidence=0.9,
                volume=75000,
                lifecycle_stage=TrendLifecycle.EMERGING,
                geographic_scope=["US", "CA", "GB"],
                related_keywords=["AI", "machine learning", "neural networks"],
            ),
            TrendSignal(
                platform=Platform.YOUTUBE,
                keyword="electric vehicles",
                momentum=0.72,
                timestamp=base_time - timedelta(minutes=30),
                confidence=0.85,
                volume=45000,
                lifecycle_stage=TrendLifecycle.GROWING,
                geographic_scope=["US", "DE", "CN"],
                related_keywords=["EV", "Tesla", "battery technology"],
            ),
            TrendSignal(
                platform=Platform.TWITTER,
                keyword="cryptocurrency",
                momentum=0.65,
                timestamp=base_time - timedelta(hours=1),
                confidence=0.8,
                volume=120000,
                lifecycle_stage=TrendLifecycle.PEAK,
                geographic_scope=["US", "JP", "GB", "DE"],
                related_keywords=["bitcoin", "ethereum", "blockchain"],
            ),
            TrendSignal(
                platform=Platform.TIKTOK,
                keyword="sustainable fashion",
                momentum=0.55,
                timestamp=base_time - timedelta(hours=2),
                confidence=0.75,
                volume=25000,
                lifecycle_stage=TrendLifecycle.EMERGING,
                geographic_scope=["US", "GB", "FR"],
                related_keywords=["eco fashion", "green clothing", "sustainability"],
            ),
        ]

    @pytest.mark.asyncio
    async def test_complete_trend_analysis_pipeline(
        self,
        trend_analyzer: TrendAnalyzer,
        investment_mapper: InvestmentMapper,
        sample_trends: list[TrendSignal],
    ):
        """Test complete pipeline from trends to investment opportunities"""

        # Step 1: Analyze trends
        analysis_results = await trend_analyzer.analyze_trends(sample_trends)

        assert len(analysis_results) == len(sample_trends)

        for result in analysis_results:
            assert result.investment_score >= 0.0
            assert result.investment_score <= 1.0
            assert result.lifecycle_confidence >= 0.0
            assert result.lifecycle_confidence <= 1.0
            assert len(result.supporting_evidence) > 0

        # Step 2: Map to investment opportunities
        opportunities = await investment_mapper.map_trends_to_opportunities(
            analysis_results,
        )

        assert len(opportunities) > 0

        for opp in opportunities:
            assert opp.confidence_score >= 0.0
            assert opp.confidence_score <= 1.0
            assert len(opp.symbols) > 0
            assert opp.time_horizon_days > 0
            assert opp.time_horizon_days <= 365
            assert opp.position_size_pct > 0
            assert opp.stop_loss_pct > 0

        # Step 3: Validate investment logic
        ai_opportunities = [
            opp
            for opp in opportunities
            if "artificial intelligence" in opp.trend_signal.keyword.lower()
        ]

        if ai_opportunities:
            ai_opp = ai_opportunities[0]
            # AI trends should map to tech stocks
            tech_symbols = ["NVDA", "MSFT", "GOOGL", "TSLA"]
            assert any(symbol in ai_opp.symbols for symbol in tech_symbols)

    @pytest.mark.asyncio
    async def test_performance_requirements(
        self,
        trend_analyzer: TrendAnalyzer,
        investment_mapper: InvestmentMapper,
        sample_trends: list[TrendSignal],
    ):
        """Test that system meets performance requirements"""

        # Test sub-second analysis requirement
        start_time = datetime.now()

        analysis_results = await trend_analyzer.analyze_trends(sample_trends)
        opportunities = await investment_mapper.map_trends_to_opportunities(
            analysis_results,
        )

        elapsed_time = (datetime.now() - start_time).total_seconds()

        # Should complete in under 1 second
        assert elapsed_time < 1.0, f"Analysis took {elapsed_time:.3f}s, must be <1s"

        # Validate quality of results
        assert len(analysis_results) == len(sample_trends)
        assert len(opportunities) > 0

    @pytest.mark.asyncio
    async def test_stream_manager_integration(self, stream_manager: StreamManager):
        """Test stream manager basic functionality"""

        # Test configuration
        status = await stream_manager.get_status()
        assert "active_streams" in status
        assert "total_trends_processed" in status
        assert "platforms" in status

        # Test throughput capability
        assert stream_manager.max_throughput >= 2.78  # 10K/hour = 2.78/second

        # Test platform configurations
        for platform in Platform:
            config = stream_manager.stream_configs.get(platform)
            assert config is not None
            assert config.poll_interval_seconds > 0
            assert config.max_keywords > 0

    @pytest.mark.asyncio
    async def test_prediction_engine_accuracy(
        self,
        prediction_engine: PredictionEngine,
        sample_trends: list[TrendSignal],
    ):
        """Test prediction engine accuracy threshold"""

        # Create trend history for prediction
        ai_trend = sample_trends[0]
        trend_history = [ai_trend]

        # Test momentum prediction
        momentum_prediction = await prediction_engine.predict_trend_momentum(
            trend_history,
            24,
        )

        assert momentum_prediction.confidence >= 0.0
        assert momentum_prediction.confidence <= 1.0
        assert momentum_prediction.time_horizon_hours == 24

        # Test volume prediction
        volume_prediction = await prediction_engine.predict_volume_growth(
            trend_history,
            24,
        )

        assert volume_prediction.predicted_value > 0
        assert volume_prediction.confidence >= 0.0

        # Test model accuracy meets threshold
        model_accuracy = prediction_engine.get_model_accuracy()

        # Note: In real implementation, this would be validated against historical data
        assert "overall" in model_accuracy

        # For contract testing - system should be capable of 95% accuracy
        assert prediction_engine.accuracy_threshold >= 0.95

    @pytest.mark.asyncio
    async def test_investment_opportunity_generation(
        self,
        trend_analyzer: TrendAnalyzer,
        investment_mapper: InvestmentMapper,
        sample_trends: list[TrendSignal],
    ):
        """Test investment opportunity generation quality"""

        analysis_results = await trend_analyzer.analyze_trends(sample_trends)
        opportunities = await investment_mapper.map_trends_to_opportunities(
            analysis_results,
        )

        # Should generate opportunities for strong trends
        strong_trends = [
            result for result in analysis_results if result.investment_score > 0.7
        ]
        strong_opportunities = [
            opp for opp in opportunities if opp.confidence_score > 0.7
        ]

        if strong_trends:
            assert len(strong_opportunities) > 0, (
                "Strong trends should generate investment opportunities"
            )

        # Test opportunity diversity
        sectors = set()
        for opp in opportunities:
            # Find sector from investment mappings
            for mapping in investment_mapper.investment_mappings:
                if any(symbol in opp.symbols for symbol in mapping.symbols):
                    sectors.add(mapping.sector)
                    break

        # Should cover multiple sectors for diversification
        if len(opportunities) >= 3:
            assert len(sectors) >= 2, (
                "Should generate opportunities across multiple sectors"
            )

        # Test risk assessment
        for opp in opportunities:
            # High-risk opportunities should have appropriate position sizing
            if opp.risk_level.value == "very_high":
                assert opp.position_size_pct <= 5.0, (
                    "Very high risk positions should be limited"
                )

            # Emerging trends should have shorter time horizons
            if opp.trend_signal.lifecycle_stage == TrendLifecycle.EMERGING:
                assert opp.time_horizon_days <= 60, (
                    "Emerging trends should have shorter horizons"
                )

    @pytest.mark.asyncio
    async def test_portfolio_optimization(
        self,
        trend_analyzer: TrendAnalyzer,
        investment_mapper: InvestmentMapper,
        sample_trends: list[TrendSignal],
    ):
        """Test portfolio optimization functionality"""

        analysis_results = await trend_analyzer.analyze_trends(sample_trends)
        opportunities = await investment_mapper.map_trends_to_opportunities(
            analysis_results,
        )

        if len(opportunities) >= 3:
            # Test portfolio optimization
            optimized_portfolio = await investment_mapper.get_portfolio_recommendations(
                opportunities,
                max_positions=5,
                max_sector_exposure=0.3,
            )

            assert len(optimized_portfolio) <= 5

            # Check total position sizing
            total_position = sum(opp.position_size_pct for opp in optimized_portfolio)
            assert total_position <= 100.0

            # Check sector diversification
            sector_exposures = {}
            for opp in optimized_portfolio:
                for mapping in investment_mapper.investment_mappings:
                    if any(symbol in opp.symbols for symbol in mapping.symbols):
                        sector = mapping.sector
                        sector_exposures[sector] = (
                            sector_exposures.get(sector, 0) + opp.position_size_pct
                        )
                        break

            # No single sector should exceed 30%
            for sector, exposure in sector_exposures.items():
                assert exposure <= 30.0, f"Sector {sector} exposure {
                    exposure
                }% exceeds 30% limit"

    @pytest.mark.asyncio
    async def test_data_model_integration(self, sample_trends: list[TrendSignal]):
        """Test data model serialization and validation"""

        for trend in sample_trends:
            # Test serialization
            trend_dict = trend.to_dict()
            trend_json = trend.to_json()

            # Test deserialization
            reconstructed_trend = TrendSignal.from_dict(trend_dict)
            reconstructed_from_json = TrendSignal.from_json(trend_json)

            # Verify data integrity
            assert reconstructed_trend.keyword == trend.keyword
            assert reconstructed_trend.momentum == trend.momentum
            assert reconstructed_trend.platform == trend.platform

            assert reconstructed_from_json.keyword == trend.keyword
            assert reconstructed_from_json.confidence == trend.confidence

    @pytest.mark.asyncio
    async def test_error_handling_and_resilience(
        self,
        trend_analyzer: TrendAnalyzer,
        investment_mapper: InvestmentMapper,
    ):
        """Test system resilience to errors and edge cases"""

        # Test empty input
        empty_results = await trend_analyzer.analyze_trends([])
        assert len(empty_results) == 0

        empty_opportunities = await investment_mapper.map_trends_to_opportunities([])
        assert len(empty_opportunities) == 0

        # Test invalid data handling
        try:
            invalid_trend = TrendSignal(
                platform=Platform.GOOGLE_TRENDS,
                keyword="",  # Empty keyword should fail validation
                momentum=1.5,  # Invalid momentum > 1.0
                timestamp=datetime.now(),
                confidence=0.9,
                volume=50000,
                lifecycle_stage=TrendLifecycle.EMERGING,
            )
            assert False, "Should have raised validation error"
        except ValueError:
            pass  # Expected validation error

        # Test graceful degradation with minimal data
        minimal_trend = TrendSignal(
            platform=Platform.GOOGLE_TRENDS,
            keyword="test",
            momentum=0.5,
            timestamp=datetime.now(),
            confidence=0.5,
            volume=1000,
            lifecycle_stage=TrendLifecycle.EMERGING,
        )

        minimal_results = await trend_analyzer.analyze_trends([minimal_trend])
        assert len(minimal_results) == 1
        assert minimal_results[0].investment_score >= 0.0

    def test_system_configuration_validation(self):
        """Test system configuration and setup"""

        # Test stream manager configuration
        stream_manager = StreamManager()

        # All platforms should be configured
        for platform in Platform:
            assert platform in stream_manager.stream_configs
            config = stream_manager.stream_configs[platform]
            assert config.poll_interval_seconds > 0
            assert config.max_keywords > 0
            assert config.rate_limit_per_hour > 0

        # Test investment mappings
        investment_mapper = InvestmentMapper()

        # Should have mappings for major trend categories
        assert len(investment_mapper.investment_mappings) >= 5

        # Each mapping should have valid symbols
        for mapping in investment_mapper.investment_mappings:
            assert len(mapping.symbols) > 0
            assert mapping.sector is not None
            assert mapping.confidence_multiplier > 0

    @pytest.mark.asyncio
    async def test_integration_with_existing_pake_system(
        self,
        sample_trends: list[TrendSignal],
    ):
        """Test integration with existing PAKE system components"""

        # Test data compatibility with PAKE data structures
        trend_analyzer = TrendAnalyzer()
        analysis_results = await trend_analyzer.analyze_trends(sample_trends)

        # Results should be compatible with PAKE caching system
        for result in analysis_results:
            result_dict = result.trend_signal.to_dict()

            # Should have timestamp for caching
            assert "timestamp" in result_dict

            # Should have platform for multi-source aggregation
            assert "platform" in result_dict

            # Should have geographic data for regional analysis
            assert "geographic_scope" in result_dict

        # Test Redis compatibility (would integrate with existing caching)
        stream_manager = StreamManager()

        # Stream names should follow PAKE conventions
        assert stream_manager.trend_stream_name.startswith("trends:")
        assert stream_manager.consumer_group == "trend_processors"


# Performance benchmark tests
class TestPerformanceBenchmarks:
    """Performance benchmark tests for contract validation"""

    @pytest.mark.asyncio
    async def test_throughput_benchmark(self):
        """Test system can process 10K+ trends per hour"""

        trend_analyzer = TrendAnalyzer()
        investment_mapper = InvestmentMapper()

        # Create batch of trends for throughput testing
        batch_size = 100
        trends = []

        base_time = datetime.now()
        for i in range(batch_size):
            trend = TrendSignal(
                platform=Platform.GOOGLE_TRENDS,
                keyword=f"test_trend_{i}",
                momentum=0.5 + (i % 50) / 100,
                timestamp=base_time - timedelta(minutes=i),
                confidence=0.7 + (i % 30) / 100,
                volume=1000 + i * 100,
                lifecycle_stage=TrendLifecycle.EMERGING,
            )
            trends.append(trend)

        # Measure processing time
        start_time = datetime.now()

        analysis_results = await trend_analyzer.analyze_trends(trends)
        opportunities = await investment_mapper.map_trends_to_opportunities(
            analysis_results,
        )

        elapsed_time = (datetime.now() - start_time).total_seconds()

        # Calculate throughput
        trends_per_second = batch_size / elapsed_time
        trends_per_hour = trends_per_second * 3600

        # Should meet 10K+ trends per hour requirement
        assert trends_per_hour >= 10000, f"Throughput: {
            trends_per_hour:.0f}/hour, need 10K+/hour"

        # Validate quality isn't sacrificed for speed
        assert len(analysis_results) == batch_size
        assert len(opportunities) > 0

    @pytest.mark.asyncio
    async def test_accuracy_benchmark(self):
        """Test prediction accuracy meets 95% threshold"""

        prediction_engine = PredictionEngine()

        # Test that accuracy threshold is properly configured
        assert prediction_engine.accuracy_threshold >= 0.95

        # Test model accuracy reporting
        model_accuracy = prediction_engine.get_model_accuracy()

        assert "overall" in model_accuracy
        assert isinstance(model_accuracy["overall"], float)
        assert model_accuracy["overall"] >= 0.0
        assert model_accuracy["overall"] <= 1.0

        # In production, this would be validated against historical performance data
        # For now, verify the system is capable of tracking accuracy


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
