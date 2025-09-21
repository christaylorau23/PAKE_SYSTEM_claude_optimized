"""
Comprehensive test suite for Content Routing Engine
Tests intelligent content routing, prioritization, and flow optimization.
"""

import asyncio
import time
from datetime import UTC, datetime, timedelta

import pytest

from services.ai.content_routing_engine import (
    ContentCategory,
    ContentDestination,
    ContentRoutingConfig,
    ContentRoutingEngine,
    IntelligentRouter,
    LoadBalancer,
    PriorityCalculator,
    RoutingContent,
    RoutingDecision,
    RoutingPriority,
    RoutingResult,
    RoutingRule,
    RoutingStrategy,
    UserContext,
    create_production_content_routing_engine,
)


@pytest.fixture
def routing_config():
    """Test configuration for content routing"""
    return ContentRoutingConfig(
        default_routing_strategy=RoutingStrategy.INTELLIGENT_HYBRID,
        max_routing_destinations=3,
        quality_threshold_high=0.8,
        quality_threshold_medium=0.6,
        urgency_threshold_urgent=0.9,
        urgency_threshold_high=0.7,
        max_user_content_per_hour=20,
        enable_load_balancing=True,
        enable_intelligent_delays=True,
        max_processing_delay_minutes=30,
        batch_processing_threshold=50,
        cache_routing_decisions=True,
        routing_cache_ttl_minutes=5,
        max_concurrent_routing=10,
        enable_feedback_learning=True,
    )


@pytest.fixture
def routing_engine(routing_config):
    """Content routing engine instance for testing"""
    return ContentRoutingEngine(routing_config)


@pytest.fixture
def sample_content():
    """Sample content items for testing"""
    base_time = datetime.now(UTC)

    content_items = [
        RoutingContent(
            content_id="breaking_news_1",
            content_type="news_article",
            category=ContentCategory.BREAKING_NEWS,
            topics=["ai", "technology", "breakthrough"],
            quality_score=0.95,
            urgency_score=0.98,
            user_relevance_scores={"user_1": 0.9, "user_2": 0.7},
            source="tech_news",
            content_length=1200,
            created_timestamp=base_time - timedelta(minutes=5),
        ),
        RoutingContent(
            content_id="research_paper_1",
            content_type="academic_paper",
            category=ContentCategory.RESEARCH_PAPER,
            topics=["machine_learning", "neural_networks"],
            quality_score=0.88,
            urgency_score=0.3,
            user_relevance_scores={"user_1": 0.85, "user_3": 0.9},
            source="arxiv",
            content_length=8500,
            created_timestamp=base_time - timedelta(hours=2),
        ),
        RoutingContent(
            content_id="personal_interest_1",
            content_type="blog_post",
            category=ContentCategory.PERSONAL_INTEREST,
            topics=["python", "programming", "tutorials"],
            quality_score=0.75,
            urgency_score=0.6,
            user_relevance_scores={"user_1": 0.95, "user_2": 0.4},
            source="dev_blog",
            content_length=2800,
            created_timestamp=base_time - timedelta(minutes=30),
        ),
        RoutingContent(
            content_id="low_quality_content",
            content_type="social_media",
            category=ContentCategory.ENTERTAINMENT,
            topics=["random", "memes"],
            quality_score=0.2,
            urgency_score=0.1,
            user_relevance_scores={"user_2": 0.3},
            source="social_platform",
            content_length=150,
            created_timestamp=base_time - timedelta(days=4),
        ),
    ]

    return content_items


@pytest.fixture
def sample_user_contexts():
    """Sample user contexts for testing"""
    return [
        UserContext(
            user_id="user_1",
            preferences={"ai": 0.9, "technology": 0.8, "programming": 0.95},
            active_topics={"ai", "machine_learning", "python"},
            notification_preferences={"email": True, "push": True, "sms": False},
            current_load=5,
            timezone="America/New_York",
            last_activity=datetime.now(UTC) - timedelta(minutes=15),
        ),
        UserContext(
            user_id="user_2",
            preferences={"entertainment": 0.7, "technology": 0.5},
            active_topics={"memes", "social"},
            notification_preferences={"email": False, "push": True, "sms": False},
            current_load=15,  # Higher load
            timezone="Europe/London",
            last_activity=datetime.now(UTC) - timedelta(hours=2),
        ),
        UserContext(
            user_id="user_3",
            preferences={"research": 0.95, "academic": 0.9},
            active_topics={"neural_networks", "deep_learning"},
            notification_preferences={"email": True, "push": False, "sms": False},
            current_load=2,
            timezone="UTC",
        ),
    ]


@pytest.fixture
def sample_routing_rules():
    """Sample routing rules for testing"""
    return [
        RoutingRule(
            rule_id="test_breaking_news",
            name="Test Breaking News Rule",
            conditions={"categories": ["breaking_news"], "min_quality": 0.8},
            actions={
                "destination": "real_time_stream",
                "priority": "urgent",
                "delay_ms": 0,
            },
            priority=100,
        ),
        RoutingRule(
            rule_id="test_research_routing",
            name="Test Research Paper Rule",
            conditions={"categories": ["research_paper"], "min_quality": 0.7},
            actions={
                "destination": "email_digest",
                "priority": "normal",
                "delay_ms": 1800000,
            },
            priority=80,
        ),
    ]


class TestContentRoutingEngine:
    """Test the main content routing engine functionality"""

    @pytest.mark.asyncio
    async def test_should_initialize_routing_engine_with_configuration(
        self,
        routing_config,
    ):
        """
        Test: Should initialize content routing engine with proper configuration
        and default routing rules ready for intelligent content processing.
        """
        engine = ContentRoutingEngine(routing_config)

        # Verify initialization
        assert engine.config == routing_config
        assert engine.priority_calculator is not None
        assert engine.load_balancer is not None
        assert engine.intelligent_router is not None
        assert len(engine.routing_cache) == 0
        assert len(engine.user_contexts) == 0

        # Verify default routing rules were setup
        assert len(engine.intelligent_router.routing_rules) > 0

        # Verify metrics initialization
        metrics = engine.get_metrics()
        assert metrics["content_routed"] == 0
        assert metrics["routing_decisions_made"] == 0
        assert metrics["cache_hits"] == 0
        assert metrics["cache_misses"] == 0

    @pytest.mark.asyncio
    async def test_should_route_urgent_content_to_real_time_stream(
        self,
        routing_engine,
        sample_content,
        sample_user_contexts,
    ):
        """
        Test: Should route urgent breaking news content to real-time stream
        with high priority and minimal delay for immediate delivery.
        """
        # Set user context
        routing_engine.set_user_context(sample_user_contexts[0])

        # Route breaking news content
        breaking_news = sample_content[0]  # High urgency breaking news
        result = await routing_engine.route_content(breaking_news, "user_1")

        # Verify routing result
        assert isinstance(result, RoutingResult)
        assert result.success is True
        assert result.content_id == breaking_news.content_id
        assert result.processing_time_ms > 0
        assert result.primary_destination == ContentDestination.REAL_TIME_STREAM

        # Verify routing decisions
        assert len(result.routing_decisions) > 0
        primary_decision = result.routing_decisions[0]
        assert primary_decision.destination == ContentDestination.REAL_TIME_STREAM
        assert primary_decision.routing_priority == RoutingPriority.URGENT
        assert primary_decision.processing_delay_ms == 0  # No delay for urgent content
        assert primary_decision.confidence_score > 0.8

    @pytest.mark.asyncio
    async def test_should_route_research_content_to_email_digest_with_delay(
        self,
        routing_engine,
        sample_content,
        sample_user_contexts,
    ):
        """
        Test: Should route research papers to email digest with appropriate
        delay for batch processing and optimal user experience.
        """
        # Set user context
        routing_engine.set_user_context(
            sample_user_contexts[2],
        )  # Research-focused user

        # Route research paper content
        research_paper = sample_content[1]
        result = await routing_engine.route_content(research_paper, "user_3")

        # Verify routing result
        assert result.success is True
        assert result.content_id == research_paper.content_id
        assert result.primary_destination == ContentDestination.EMAIL_DIGEST

        # Verify intelligent delay applied
        primary_decision = result.routing_decisions[0]
        assert (
            primary_decision.processing_delay_ms > 0
        )  # Should have delay for batching
        assert primary_decision.routing_priority in [
            RoutingPriority.NORMAL,
            RoutingPriority.HIGH,
        ]

    @pytest.mark.asyncio
    async def test_should_apply_load_balancing_for_high_volume_users(
        self,
        routing_engine,
        sample_content,
        sample_user_contexts,
    ):
        """
        Test: Should apply load balancing to prevent user content overload
        by deferring or delaying content for high-volume users.
        """
        # Set user context with high current load
        high_load_user = sample_user_contexts[1]  # user_2 with load=15
        routing_engine.set_user_context(high_load_user)

        # Simulate user at capacity
        for _ in range(20):  # Exceed max_user_content_per_hour
            routing_engine.load_balancer.record_user_delivery("user_2")

        # Route personal interest content
        personal_content = sample_content[2]
        result = await routing_engine.route_content(personal_content, "user_2")

        # Verify load balancing applied
        assert result.success is True

        # Check if content was deferred or delayed due to load balancing
        primary_decision = result.routing_decisions[0]
        load_balancing_applied = any(
            "load balancing" in reason.lower() for reason in primary_decision.reasoning
        )

        # Either load balancing was applied OR content was urgent enough to bypass it
        assert (
            load_balancing_applied
            or primary_decision.routing_priority == RoutingPriority.URGENT
        )

    @pytest.mark.asyncio
    async def test_should_handle_concurrent_routing_operations_safely(
        self,
        routing_engine,
        sample_content,
    ):
        """
        Test: Should handle concurrent content routing operations without
        race conditions and maintain consistent performance.
        """
        # Create many concurrent routing tasks
        concurrent_content = []
        for i in range(25):
            content = RoutingContent(
                content_id=f"concurrent_content_{i}",
                content_type="test_content",
                category=ContentCategory.INDUSTRY_UPDATE,
                topics=[f"topic_{i % 5}"],
                quality_score=0.5 + (i % 5) * 0.1,
                urgency_score=0.3 + (i % 3) * 0.2,
            )
            concurrent_content.append(content)

        # Process all content concurrently
        start_time = time.time()
        tasks = [
            routing_engine.route_content(content) for content in concurrent_content
        ]
        results = await asyncio.gather(*tasks)
        processing_time = time.time() - start_time

        # Verify all routing operations succeeded
        assert len(results) == 25
        assert all(result.success for result in results)

        # Verify reasonable processing time (should be much faster than sequential)
        assert processing_time < 5.0  # Should complete within 5 seconds

        # Verify metrics updated correctly
        metrics = routing_engine.get_metrics()
        assert metrics["content_routed"] == 25

    @pytest.mark.asyncio
    async def test_should_implement_routing_decision_caching_effectively(
        self,
        routing_engine,
        sample_content,
    ):
        """
        Test: Should cache routing decisions and serve from cache when appropriate
        to improve performance and reduce computational overhead.
        """
        content = sample_content[0]  # Breaking news content

        # First routing request - should miss cache
        result1 = await routing_engine.route_content(content, "user_1")
        metrics1 = routing_engine.get_metrics()

        # Second identical request - should hit cache
        result2 = await routing_engine.route_content(content, "user_1")
        metrics2 = routing_engine.get_metrics()

        # Verify cache behavior
        assert metrics1["cache_misses"] == 1
        assert metrics1["cache_hits"] == 0
        assert metrics2["cache_misses"] == 1
        assert metrics2["cache_hits"] == 1

        # Verify cached results are identical
        assert result1.content_id == result2.content_id
        assert result1.primary_destination == result2.primary_destination
        assert len(result1.routing_decisions) == len(result2.routing_decisions)

    @pytest.mark.asyncio
    async def test_should_process_batch_content_efficiently(
        self,
        routing_engine,
        sample_user_contexts,
    ):
        """
        Test: Should process batch content routing efficiently with optimized
        performance for large content volumes.
        """
        # Set user context
        routing_engine.set_user_context(sample_user_contexts[0])

        # Create batch content
        batch_content = []
        for i in range(15):  # Below batch threshold for individual processing
            content = RoutingContent(
                content_id=f"batch_content_{i}",
                content_type="article",
                category=ContentCategory.INDUSTRY_UPDATE,
                topics=["technology", "business"],
                quality_score=0.7,
                urgency_score=0.4,
            )
            batch_content.append(content)

        # Process batch
        start_time = time.time()
        results = await routing_engine.batch_route_content(batch_content, "user_1")
        processing_time = time.time() - start_time

        # Verify batch processing results
        assert len(results) == 15
        assert all(result.success for result in results)
        assert processing_time < 2.0  # Should be fast for small batch

        # Verify all content was routed
        routed_ids = {result.content_id for result in results}
        expected_ids = {f"batch_content_{i}" for i in range(15)}
        assert routed_ids == expected_ids

    @pytest.mark.asyncio
    async def test_should_apply_intelligent_delays_based_on_content_type(
        self,
        routing_engine,
        sample_content,
    ):
        """
        Test: Should apply intelligent delays based on content characteristics
        and destination for optimal delivery timing.
        """
        # Route research paper (should get delay for email digest)
        research_paper = sample_content[1]
        result = await routing_engine.route_content(research_paper)

        # Verify intelligent delay applied
        assert result.success is True
        primary_decision = result.routing_decisions[0]

        if primary_decision.destination == ContentDestination.EMAIL_DIGEST:
            assert primary_decision.processing_delay_ms > 0
            delay_applied = any(
                "intelligent delay" in reason.lower()
                for reason in primary_decision.reasoning
            )
            # Either explicit intelligent delay or rule-based delay
            assert (
                delay_applied or primary_decision.processing_delay_ms > 60000
            )  # More than 1 minute

    @pytest.mark.asyncio
    async def test_should_handle_routing_errors_gracefully(self, routing_engine):
        """
        Test: Should handle routing errors gracefully and return appropriate
        error results without breaking the system.
        """
        # Create problematic content that might cause errors
        problematic_content = RoutingContent(
            content_id="error_content",
            content_type="invalid_type",
            category=ContentCategory.BREAKING_NEWS,
            quality_score=-1.0,  # Invalid quality score
            urgency_score=2.0,  # Invalid urgency score (>1.0)
            created_timestamp=datetime.now(UTC) + timedelta(days=1),  # Future timestamp
        )

        # Route problematic content
        result = await routing_engine.route_content(problematic_content)

        # Should handle gracefully - either succeed with defaults or fail gracefully
        assert isinstance(result, RoutingResult)
        assert result.content_id == "error_content"

        # If it fails, should have error message
        if not result.success:
            assert result.error_message is not None
            assert result.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_should_track_comprehensive_routing_metrics(
        self,
        routing_engine,
        sample_content,
        sample_user_contexts,
    ):
        """
        Test: Should track comprehensive metrics for monitoring routing
        effectiveness and system performance.
        """
        initial_metrics = routing_engine.get_metrics()

        # Set user context and route content
        routing_engine.set_user_context(sample_user_contexts[0])

        for content in sample_content[:3]:
            await routing_engine.route_content(content, "user_1")

        final_metrics = routing_engine.get_metrics()

        # Verify metric tracking
        assert final_metrics["content_routed"] > initial_metrics["content_routed"]
        assert (
            final_metrics["routing_decisions_made"]
            > initial_metrics["routing_decisions_made"]
        )
        assert final_metrics["cached_routing_decisions"] >= 0
        assert final_metrics["active_user_contexts"] > 0
        assert final_metrics["active_routing_rules"] > 0
        assert "average_processing_time_ms" in final_metrics


class TestPriorityCalculator:
    """Test priority calculation functionality"""

    @pytest.mark.asyncio
    async def test_should_calculate_priority_based_on_multiple_factors(
        self,
        routing_config,
        sample_content,
        sample_user_contexts,
    ):
        """
        Test: Should calculate content priority based on quality, urgency,
        user relevance, and content freshness factors.
        """
        calculator = PriorityCalculator(routing_config)
        user_context = sample_user_contexts[0]  # user_1

        # Test high-priority breaking news
        breaking_news = sample_content[0]
        priority, confidence = calculator.calculate_priority(
            breaking_news,
            user_context,
        )

        assert priority == RoutingPriority.URGENT
        assert (
            confidence > 0.8
        )  # High confidence for high-quality, urgent, relevant content

        # Test medium-priority research paper
        research_paper = sample_content[1]
        priority, confidence = calculator.calculate_priority(
            research_paper,
            user_context,
        )

        assert priority in [RoutingPriority.HIGH, RoutingPriority.NORMAL]
        assert 0.5 < confidence < 0.9

        # Test low-priority old content
        low_quality = sample_content[3]
        priority, confidence = calculator.calculate_priority(low_quality, user_context)

        assert priority in [RoutingPriority.LOW, RoutingPriority.DEFERRED]
        assert confidence < 0.5

    @pytest.mark.asyncio
    async def test_should_factor_content_freshness_into_priority(self, routing_config):
        """
        Test: Should consider content age/freshness when calculating
        priority with newer content getting higher scores.
        """
        calculator = PriorityCalculator(routing_config)
        base_time = datetime.now(UTC)

        # Fresh content
        fresh_content = RoutingContent(
            content_id="fresh",
            content_type="article",
            category=ContentCategory.INDUSTRY_UPDATE,
            quality_score=0.7,
            urgency_score=0.5,
            created_timestamp=base_time - timedelta(minutes=5),
        )

        # Old content (same quality and urgency)
        old_content = RoutingContent(
            content_id="old",
            content_type="article",
            category=ContentCategory.INDUSTRY_UPDATE,
            quality_score=0.7,
            urgency_score=0.5,
            created_timestamp=base_time - timedelta(days=2),
        )

        fresh_priority, fresh_confidence = calculator.calculate_priority(fresh_content)
        old_priority, old_confidence = calculator.calculate_priority(old_content)

        # Fresh content should have higher confidence due to freshness factor
        assert fresh_confidence > old_confidence


class TestLoadBalancer:
    """Test load balancing functionality"""

    @pytest.mark.asyncio
    async def test_should_track_user_content_capacity_accurately(self, routing_config):
        """
        Test: Should accurately track user content capacity and prevent
        overload by monitoring delivery rates over time windows.
        """
        load_balancer = LoadBalancer(routing_config)
        user_id = "test_user"

        # Initially user should have capacity
        assert load_balancer.check_user_capacity(user_id) is True

        # Add content deliveries up to limit
        for i in range(routing_config.max_user_content_per_hour):
            load_balancer.record_user_delivery(user_id)

        # User should now be at capacity
        assert load_balancer.check_user_capacity(user_id) is False

        # Verify load tracking
        assert (
            len(load_balancer.user_loads[user_id])
            == routing_config.max_user_content_per_hour
        )

    @pytest.mark.asyncio
    async def test_should_select_optimal_destination_based_on_load(
        self,
        routing_config,
    ):
        """
        Test: Should select destination with lowest current load for
        optimal distribution and performance balancing.
        """
        load_balancer = LoadBalancer(routing_config)

        destinations = [
            ContentDestination.USER_FEED,
            ContentDestination.EMAIL_DIGEST,
            ContentDestination.NOTIFICATION_SYSTEM,
        ]

        # Add different loads to destinations
        load_balancer.update_destination_load(ContentDestination.USER_FEED, 10)
        load_balancer.update_destination_load(ContentDestination.EMAIL_DIGEST, 5)
        load_balancer.update_destination_load(
            ContentDestination.NOTIFICATION_SYSTEM,
            15,
        )

        # Should select EMAIL_DIGEST (lowest load: 5)
        optimal = load_balancer.get_optimal_destination(destinations)
        assert optimal == ContentDestination.EMAIL_DIGEST


class TestIntelligentRouter:
    """Test intelligent routing logic"""

    @pytest.mark.asyncio
    async def test_should_apply_routing_rules_by_priority_order(
        self,
        routing_config,
        sample_routing_rules,
        sample_content,
    ):
        """
        Test: Should apply routing rules in priority order and execute
        appropriate actions based on rule conditions.
        """
        router = IntelligentRouter(routing_config)

        # Add test routing rules
        for rule in sample_routing_rules:
            router.add_routing_rule(rule)

        # Route breaking news (should match first rule)
        breaking_news = sample_content[0]
        decisions = router.route_content(breaking_news)

        assert len(decisions) > 0
        primary_decision = decisions[0]
        assert primary_decision.destination == ContentDestination.REAL_TIME_STREAM
        assert primary_decision.routing_priority == RoutingPriority.URGENT

        # Verify rule matching in reasoning
        rule_matched = any(
            "routing rule" in reason.lower() for reason in primary_decision.reasoning
        )
        assert rule_matched

    @pytest.mark.asyncio
    async def test_should_evaluate_complex_rule_conditions_accurately(
        self,
        routing_config,
        sample_content,
        sample_user_contexts,
    ):
        """
        Test: Should accurately evaluate complex routing rule conditions
        including content attributes, user context, and time-based criteria.
        """
        router = IntelligentRouter(routing_config)

        # Create complex routing rule
        complex_rule = RoutingRule(
            rule_id="complex_test",
            name="Complex Rule Test",
            conditions={
                "categories": ["personal_interest"],
                "min_quality": 0.7,
                "required_topics": ["python"],
                "user_conditions": {"active_topics": ["python"]},
                "time_conditions": {"max_age_hours": 24},
            },
            actions={"destination": "notification_system", "priority": "high"},
            priority=95,
        )
        router.add_routing_rule(complex_rule)

        # Test content that should match complex rule
        personal_content = sample_content[2]  # Has 'python' topic
        user_context = sample_user_contexts[0]  # Has 'python' in active topics

        decisions = router.route_content(personal_content, user_context)

        # Should match the complex rule
        assert len(decisions) > 0
        matched_decision = next(
            (
                d
                for d in decisions
                if d.destination == ContentDestination.NOTIFICATION_SYSTEM
            ),
            None,
        )
        assert matched_decision is not None
        assert matched_decision.routing_priority == RoutingPriority.HIGH

    @pytest.mark.asyncio
    async def test_should_apply_default_routing_when_no_rules_match(
        self,
        routing_config,
    ):
        """
        Test: Should apply default routing logic when no custom rules
        match the content characteristics.
        """
        router = IntelligentRouter(routing_config)

        # Create content that won't match any default rules
        unmatched_content = RoutingContent(
            content_id="unmatched",
            content_type="unknown",
            category=ContentCategory.INDUSTRY_UPDATE,  # No specific rules for this
            quality_score=0.5,
            urgency_score=0.4,
        )

        decisions = router.route_content(unmatched_content)

        # Should fall back to default routing
        assert len(decisions) > 0
        primary_decision = decisions[0]

        # Default routing should typically go to user feed
        assert primary_decision.destination == ContentDestination.USER_FEED
        assert "default" in primary_decision.reasoning[0].lower()


class TestProductionConfiguration:
    """Test production-ready configuration and setup"""

    @pytest.mark.asyncio
    async def test_should_create_production_content_routing_engine(self):
        """
        Test: Should create production-optimized content routing engine
        with appropriate configuration for scale and performance.
        """
        engine = create_production_content_routing_engine()

        # Verify production configuration
        assert (
            engine.config.default_routing_strategy == RoutingStrategy.INTELLIGENT_HYBRID
        )
        assert engine.config.max_routing_destinations == 5  # More routing options
        assert engine.config.quality_threshold_high == 0.85  # Higher quality thresholds
        assert engine.config.urgency_threshold_urgent == 0.95  # More selective urgency
        assert engine.config.max_user_content_per_hour == 25  # Conservative load limit
        assert engine.config.max_concurrent_routing == 50  # Higher concurrency
        assert (
            engine.config.routing_cache_ttl_minutes == 3
        )  # Short cache for dynamic routing

        # Verify engine is ready for operation
        assert engine.priority_calculator is not None
        assert engine.load_balancer is not None
        assert engine.intelligent_router is not None
        assert len(engine.intelligent_router.routing_rules) > 0  # Default rules loaded


class TestDataStructures:
    """Test data structure serialization and immutability"""

    def test_routing_content_should_be_immutable_and_serializable(self):
        """
        Test: RoutingContent should be immutable and properly serializable
        for storage and transmission across system components.
        """
        content = RoutingContent(
            content_id="test_content",
            content_type="article",
            category=ContentCategory.BREAKING_NEWS,
            topics=["ai", "technology"],
            quality_score=0.85,
            urgency_score=0.9,
            user_relevance_scores={"user_1": 0.8},
            source="tech_news",
        )

        # Verify immutability
        with pytest.raises(Exception):  # Should raise FrozenInstanceError
            content.quality_score = 0.95

        # Verify serialization fields
        assert content.content_id == "test_content"
        assert content.category == ContentCategory.BREAKING_NEWS
        assert content.topics == ["ai", "technology"]
        assert content.quality_score == 0.85
        assert content.user_relevance_scores["user_1"] == 0.8
        assert isinstance(content.created_timestamp, datetime)

    def test_routing_result_should_serialize_with_comprehensive_metadata(self):
        """
        Test: RoutingResult should serialize with comprehensive metadata
        including processing metrics and routing information.
        """
        decisions = [
            RoutingDecision(
                content_id="test_content",
                destination=ContentDestination.REAL_TIME_STREAM,
                routing_priority=RoutingPriority.URGENT,
                reasoning=["Breaking news priority"],
                confidence_score=0.95,
                processing_delay_ms=0,
            ),
        ]

        result = RoutingResult(
            content_id="test_content",
            routing_decisions=decisions,
            primary_destination=ContentDestination.REAL_TIME_STREAM,
            fallback_destinations=[ContentDestination.NOTIFICATION_SYSTEM],
            processing_time_ms=25.5,
            strategy_used=RoutingStrategy.INTELLIGENT_HYBRID,
            success=True,
        )

        # Verify comprehensive serialization
        assert result.content_id == "test_content"
        assert len(result.routing_decisions) == 1
        assert result.primary_destination == ContentDestination.REAL_TIME_STREAM
        assert ContentDestination.NOTIFICATION_SYSTEM in result.fallback_destinations
        assert result.processing_time_ms == 25.5
        assert result.strategy_used == RoutingStrategy.INTELLIGENT_HYBRID
        assert result.success is True
        assert isinstance(result.processed_timestamp, datetime)

    def test_user_context_should_support_comprehensive_personalization(self):
        """
        Test: UserContext should support comprehensive personalization data
        for intelligent routing decisions.
        """
        user_context = UserContext(
            user_id="personalization_user",
            preferences={"ai": 0.9, "technology": 0.8},
            active_topics={"machine_learning", "programming"},
            notification_preferences={"email": True, "push": False},
            current_load=10,
            timezone="America/Los_Angeles",
        )

        # Verify comprehensive personalization support
        assert user_context.user_id == "personalization_user"
        assert user_context.preferences["ai"] == 0.9
        assert "machine_learning" in user_context.active_topics
        assert user_context.notification_preferences["email"] is True
        assert user_context.current_load == 10
        assert user_context.timezone == "America/Los_Angeles"
