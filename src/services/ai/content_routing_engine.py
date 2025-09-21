"""Intelligent Content Routing and Prioritization Engine for PAKE System
AI-driven content flow optimization with dynamic routing and smart prioritization.
"""

import asyncio
import hashlib
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class RoutingStrategy(Enum):
    """Content routing strategies"""

    PRIORITY_BASED = "priority_based"
    USER_PREFERENCE = "user_preference"
    LOAD_BALANCED = "load_balanced"
    TOPIC_SPECIALIZED = "topic_specialized"
    QUALITY_THRESHOLD = "quality_threshold"
    INTELLIGENT_HYBRID = "intelligent_hybrid"


class ContentDestination(Enum):
    """Content delivery destinations"""

    USER_FEED = "user_feed"
    NOTIFICATION_SYSTEM = "notification_system"
    EMAIL_DIGEST = "email_digest"
    ARCHIVE = "archive"
    PRIORITY_QUEUE = "priority_queue"
    REAL_TIME_STREAM = "real_time_stream"
    BATCH_PROCESSING = "batch_processing"


class RoutingPriority(Enum):
    """Content routing priority levels"""

    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    DEFERRED = "deferred"


class ContentCategory(Enum):
    """Content categories for routing decisions"""

    BREAKING_NEWS = "breaking_news"
    RESEARCH_PAPER = "research_paper"
    INDUSTRY_UPDATE = "industry_update"
    PERSONAL_INTEREST = "personal_interest"
    TRENDING_TOPIC = "trending_topic"
    EDUCATIONAL = "educational"
    ENTERTAINMENT = "entertainment"


@dataclass(frozen=True)
class RoutingContent:
    """Immutable content item for routing decisions"""

    content_id: str
    content_type: str
    category: ContentCategory
    topics: list[str] = field(default_factory=list)
    quality_score: float = 0.0
    urgency_score: float = 0.0
    user_relevance_scores: dict[str, float] = field(default_factory=dict)
    source: str | None = None
    content_length: int = 0
    created_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    expiry_timestamp: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RoutingRule:
    """Immutable routing rule definition"""

    rule_id: str
    name: str
    conditions: dict[str, Any] = field(default_factory=dict)
    actions: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    is_active: bool = True
    created_by: str = "system"
    created_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )


@dataclass(frozen=True)
class RoutingDecision:
    """Immutable routing decision result"""

    content_id: str
    destination: ContentDestination
    routing_priority: RoutingPriority
    reasoning: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    processing_delay_ms: int = 0  # Suggested delay before delivery
    metadata: dict[str, Any] = field(default_factory=dict)
    decision_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )


@dataclass(frozen=True)
class RoutingResult:
    """Immutable complete routing operation result"""

    content_id: str
    routing_decisions: list[RoutingDecision] = field(default_factory=list)
    primary_destination: ContentDestination | None = None
    fallback_destinations: list[ContentDestination] = field(default_factory=list)
    processing_time_ms: float = 0.0
    strategy_used: RoutingStrategy = RoutingStrategy.PRIORITY_BASED
    success: bool = True
    error_message: str | None = None
    processed_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )


@dataclass(frozen=True)
class UserContext:
    """User context for personalized routing"""

    user_id: str
    preferences: dict[str, float] = field(default_factory=dict)
    active_topics: set[str] = field(default_factory=set)
    notification_preferences: dict[str, bool] = field(default_factory=dict)
    current_load: int = 0  # Current content load
    timezone: str = "UTC"
    last_activity: datetime | None = None


@dataclass
class ContentRoutingConfig:
    """Configuration for content routing engine"""

    default_routing_strategy: RoutingStrategy = RoutingStrategy.INTELLIGENT_HYBRID
    max_routing_destinations: int = 3
    quality_threshold_high: float = 0.8
    quality_threshold_medium: float = 0.6
    urgency_threshold_urgent: float = 0.9
    urgency_threshold_high: float = 0.7
    max_user_content_per_hour: int = 50
    enable_load_balancing: bool = True
    enable_intelligent_delays: bool = True
    max_processing_delay_minutes: int = 30
    batch_processing_threshold: int = 100
    cache_routing_decisions: bool = True
    routing_cache_ttl_minutes: int = 5
    max_concurrent_routing: int = 20
    enable_feedback_learning: bool = True


class PriorityCalculator:
    """Calculates content priority based on multiple factors"""

    def __init__(self, config: ContentRoutingConfig):
        self.config = config
        self.priority_weights = {
            "quality_score": 0.25,
            "urgency_score": 0.35,
            "user_relevance": 0.25,
            "content_freshness": 0.15,
        }

    def calculate_priority(
        self,
        content: RoutingContent,
        user_context: UserContext | None = None,
    ) -> tuple[RoutingPriority, float]:
        """Calculate overall priority and confidence score"""
        priority_score = 0.0

        # Quality factor
        quality_factor = min(content.quality_score, 1.0)
        priority_score += quality_factor * self.priority_weights["quality_score"]

        # Urgency factor
        urgency_factor = min(content.urgency_score, 1.0)
        priority_score += urgency_factor * self.priority_weights["urgency_score"]

        # User relevance factor
        if (
            user_context
            and content.user_relevance_scores.get(user_context.user_id, 0) > 0
        ):
            relevance_factor = content.user_relevance_scores[user_context.user_id]
            priority_score += relevance_factor * self.priority_weights["user_relevance"]

        # Content freshness factor
        age_hours = (
            datetime.now(UTC) - content.created_timestamp
        ).total_seconds() / 3600
        freshness_factor = max(0, 1 - (age_hours / 24))  # Decay over 24 hours
        priority_score += freshness_factor * self.priority_weights["content_freshness"]

        # Map score to priority level
        if priority_score >= self.config.urgency_threshold_urgent:
            return RoutingPriority.URGENT, priority_score
        if priority_score >= self.config.urgency_threshold_high:
            return RoutingPriority.HIGH, priority_score
        if priority_score >= 0.5:
            return RoutingPriority.NORMAL, priority_score
        if priority_score >= 0.3:
            return RoutingPriority.LOW, priority_score
        return RoutingPriority.DEFERRED, priority_score


class LoadBalancer:
    """Manages content load balancing across users and destinations"""

    def __init__(self, config: ContentRoutingConfig):
        self.config = config
        self.user_loads: dict[str, list[datetime]] = defaultdict(list)
        self.destination_loads: dict[ContentDestination, int] = defaultdict(int)

    def check_user_capacity(self, user_id: str) -> bool:
        """Check if user can receive more content"""
        now = datetime.now(UTC)
        one_hour_ago = now - timedelta(hours=1)

        # Clean old entries
        self.user_loads[user_id] = [
            timestamp
            for timestamp in self.user_loads[user_id]
            if timestamp > one_hour_ago
        ]

        # Check capacity
        current_load = len(self.user_loads[user_id])
        return current_load < self.config.max_user_content_per_hour

    def record_user_delivery(self, user_id: str):
        """Record content delivery to user"""
        self.user_loads[user_id].append(datetime.now(UTC))

    def get_optimal_destination(
        self,
        preferred_destinations: list[ContentDestination],
    ) -> ContentDestination:
        """Get destination with lowest current load"""
        if not preferred_destinations:
            return ContentDestination.USER_FEED

        # Find destination with minimum load
        min_load = float("inf")
        optimal_destination = preferred_destinations[0]

        for destination in preferred_destinations:
            current_load = self.destination_loads[destination]
            if current_load < min_load:
                min_load = current_load
                optimal_destination = destination

        return optimal_destination

    def update_destination_load(self, destination: ContentDestination, delta: int = 1):
        """Update destination load"""
        self.destination_loads[destination] += delta


class IntelligentRouter:
    """Core intelligent routing logic with AI-driven decisions"""

    def __init__(self, config: ContentRoutingConfig):
        self.config = config
        self.routing_rules: list[RoutingRule] = []
        self.topic_specialists: dict[str, list[ContentDestination]] = {}
        self.user_patterns: dict[str, dict[str, float]] = defaultdict(
            lambda: defaultdict(float),
        )

    def add_routing_rule(self, rule: RoutingRule):
        """Add new routing rule"""
        self.routing_rules.append(rule)
        # Sort by priority (higher priority first)
        self.routing_rules.sort(key=lambda x: x.priority, reverse=True)

    def setup_topic_specialists(self, topic_mappings: dict[str, list[str]]):
        """Setup topic-specific routing destinations"""
        for topic, destinations in topic_mappings.items():
            self.topic_specialists[topic] = [
                ContentDestination(dest) for dest in destinations
            ]

    def route_content(
        self,
        content: RoutingContent,
        user_context: UserContext | None = None,
    ) -> list[RoutingDecision]:
        """Make intelligent routing decisions"""
        decisions = []

        # Apply routing rules in priority order
        for rule in self.routing_rules:
            if not rule.is_active:
                continue

            if self._evaluate_rule_conditions(rule, content, user_context):
                decision = self._create_decision_from_rule(rule, content)
                if decision:
                    decisions.append(decision)

                    # Stop if rule specifies exclusivity
                    if rule.actions.get("exclusive", False):
                        break

        # If no rules matched, apply default routing logic
        if not decisions:
            decisions.extend(self._apply_default_routing(content, user_context))

        return decisions

    def _evaluate_rule_conditions(
        self,
        rule: RoutingRule,
        content: RoutingContent,
        user_context: UserContext | None,
    ) -> bool:
        """Evaluate if routing rule conditions are met"""
        conditions = rule.conditions

        # Category condition
        if "categories" in conditions:
            if content.category.value not in conditions["categories"]:
                return False

        # Quality threshold condition
        if "min_quality" in conditions:
            if content.quality_score < conditions["min_quality"]:
                return False

        # Topic condition
        if "required_topics" in conditions:
            required_topics = set(conditions["required_topics"])
            content_topics = set(content.topics)
            if not required_topics.intersection(content_topics):
                return False

        # User-specific conditions
        if user_context and "user_conditions" in conditions:
            user_conditions = conditions["user_conditions"]

            if "active_topics" in user_conditions:
                required_user_topics = set(user_conditions["active_topics"])
                if not required_user_topics.intersection(user_context.active_topics):
                    return False

        # Time-based conditions
        if "time_conditions" in conditions:
            now = datetime.now(UTC)
            time_conditions = conditions["time_conditions"]

            if "max_age_hours" in time_conditions:
                age_hours = (now - content.created_timestamp).total_seconds() / 3600
                if age_hours > time_conditions["max_age_hours"]:
                    return False

        return True

    def _create_decision_from_rule(
        self,
        rule: RoutingRule,
        content: RoutingContent,
    ) -> RoutingDecision | None:
        """Create routing decision from matched rule"""
        actions = rule.actions

        if "destination" not in actions:
            return None

        destination = ContentDestination(actions["destination"])
        priority = RoutingPriority(actions.get("priority", "normal"))
        delay_ms = actions.get("delay_ms", 0)

        return RoutingDecision(
            content_id=content.content_id,
            destination=destination,
            routing_priority=priority,
            reasoning=[f"Matched routing rule: {rule.name}"],
            confidence_score=0.9,  # High confidence for rule-based decisions
            processing_delay_ms=delay_ms,
            metadata={"rule_id": rule.rule_id},
        )

    def _apply_default_routing(
        self,
        content: RoutingContent,
        user_context: UserContext | None,
    ) -> list[RoutingDecision]:
        """Apply default routing logic when no rules match"""
        decisions = []

        # Default routing based on content category
        if content.category == ContentCategory.BREAKING_NEWS:
            decisions.append(
                RoutingDecision(
                    content_id=content.content_id,
                    destination=ContentDestination.REAL_TIME_STREAM,
                    routing_priority=RoutingPriority.URGENT,
                    reasoning=["Breaking news requires immediate delivery"],
                    confidence_score=0.8,
                ),
            )
        elif content.category == ContentCategory.RESEARCH_PAPER:
            decisions.append(
                RoutingDecision(
                    content_id=content.content_id,
                    destination=ContentDestination.EMAIL_DIGEST,
                    routing_priority=RoutingPriority.NORMAL,
                    reasoning=["Research papers suitable for digest format"],
                    confidence_score=0.7,
                ),
            )
        else:
            # Standard user feed routing
            decisions.append(
                RoutingDecision(
                    content_id=content.content_id,
                    destination=ContentDestination.USER_FEED,
                    routing_priority=RoutingPriority.NORMAL,
                    reasoning=["Default user feed routing"],
                    confidence_score=0.6,
                ),
            )

        return decisions


class ContentRoutingEngine:
    """Main content routing and prioritization engine.
    Orchestrates intelligent content flow with AI-driven routing decisions.
    """

    def __init__(self, config: ContentRoutingConfig = None):
        self.config = config or ContentRoutingConfig()
        self.priority_calculator = PriorityCalculator(self.config)
        self.load_balancer = LoadBalancer(self.config)
        self.intelligent_router = IntelligentRouter(self.config)
        self.routing_cache: dict[str, tuple[RoutingResult, datetime]] = {}
        self.user_contexts: dict[str, UserContext] = {}
        self.routing_semaphore = asyncio.Semaphore(self.config.max_concurrent_routing)

        # Setup default routing rules
        self._setup_default_routing_rules()

        # Metrics
        self.metrics = {
            "content_routed": 0,
            "routing_decisions_made": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "rule_matches": 0,
            "default_routing_used": 0,
            "load_balancing_applied": 0,
            "intelligent_delays_applied": 0,
        }

    def _setup_default_routing_rules(self):
        """Setup default intelligent routing rules"""
        # Breaking news rule
        breaking_news_rule = RoutingRule(
            rule_id="breaking_news",
            name="Breaking News Priority Routing",
            conditions={"categories": ["breaking_news"], "min_quality": 0.7},
            actions={
                "destination": "real_time_stream",
                "priority": "urgent",
                "delay_ms": 0,
            },
            priority=100,
        )
        self.intelligent_router.add_routing_rule(breaking_news_rule)

        # High-quality research rule
        research_rule = RoutingRule(
            rule_id="quality_research",
            name="High-Quality Research Routing",
            conditions={"categories": ["research_paper"], "min_quality": 0.8},
            actions={
                "destination": "email_digest",
                "priority": "high",
                "delay_ms": 1800000,  # 30 minutes
            },
            priority=80,
        )
        self.intelligent_router.add_routing_rule(research_rule)

        # Personal interest rule
        personal_rule = RoutingRule(
            rule_id="personal_interest",
            name="Personal Interest Priority",
            conditions={
                "categories": ["personal_interest"],
                "user_conditions": {
                    "active_topics": ["required"],  # Will be dynamically evaluated
                },
            },
            actions={
                "destination": "notification_system",
                "priority": "high",
                "delay_ms": 0,
            },
            priority=90,
        )
        self.intelligent_router.add_routing_rule(personal_rule)

        # Low quality content rule
        low_quality_rule = RoutingRule(
            rule_id="low_quality_archive",
            name="Low Quality Content Archival",
            conditions={
                "min_quality": 0.0,  # Catch-all for very low quality
                "time_conditions": {"max_age_hours": 72},  # Older than 3 days
            },
            actions={
                "destination": "archive",
                "priority": "deferred",
                "delay_ms": 0,
                "exclusive": True,
            },
            priority=10,
        )
        self.intelligent_router.add_routing_rule(low_quality_rule)

    def set_user_context(self, user_context: UserContext):
        """Set or update user context for routing decisions"""
        self.user_contexts[user_context.user_id] = user_context

    async def route_content(
        self,
        content: RoutingContent,
        user_id: str | None = None,
    ) -> RoutingResult:
        """Route content with intelligent prioritization and destination selection"""
        start_time = time.time()

        try:
            async with self.routing_semaphore:
                # Check cache first
                cache_key = self._generate_cache_key(content, user_id)
                if (
                    self.config.cache_routing_decisions
                    and cache_key in self.routing_cache
                ):
                    cached_result, cached_time = self.routing_cache[cache_key]
                    cache_age_minutes = (
                        datetime.now(UTC) - cached_time
                    ).total_seconds() / 60

                    if cache_age_minutes < self.config.routing_cache_ttl_minutes:
                        self.metrics["cache_hits"] += 1
                        return cached_result
                    del self.routing_cache[cache_key]

                self.metrics["cache_misses"] += 1

                # Get user context if available
                user_context = self.user_contexts.get(user_id) if user_id else None

                # Calculate content priority
                routing_priority, confidence = (
                    self.priority_calculator.calculate_priority(content, user_context)
                )

                # Make intelligent routing decisions
                routing_decisions = self.intelligent_router.route_content(
                    content,
                    user_context,
                )

                # Apply load balancing if enabled
                if self.config.enable_load_balancing and user_context:
                    routing_decisions = self._apply_load_balancing(
                        routing_decisions,
                        user_context,
                    )

                # Apply intelligent delays if enabled
                if self.config.enable_intelligent_delays:
                    routing_decisions = self._apply_intelligent_delays(
                        routing_decisions,
                        content,
                    )

                # Select primary destination and fallbacks
                primary_destination = (
                    routing_decisions[0].destination
                    if routing_decisions
                    else ContentDestination.USER_FEED
                )
                fallback_destinations = [
                    d.destination
                    for d in routing_decisions[1 : self.config.max_routing_destinations]
                ]

                # Create routing result
                processing_time = max((time.time() - start_time) * 1000, 0.1)

                result = RoutingResult(
                    content_id=content.content_id,
                    routing_decisions=routing_decisions,
                    primary_destination=primary_destination,
                    fallback_destinations=fallback_destinations,
                    processing_time_ms=processing_time,
                    strategy_used=self.config.default_routing_strategy,
                    success=True,
                )

                # Cache result
                if self.config.cache_routing_decisions:
                    self.routing_cache[cache_key] = (result, datetime.now(UTC))

                # Update metrics
                self.metrics["content_routed"] += 1
                self.metrics["routing_decisions_made"] += len(routing_decisions)

                # Record user delivery for load balancing
                if user_context and self.load_balancer.check_user_capacity(
                    user_context.user_id,
                ):
                    self.load_balancer.record_user_delivery(user_context.user_id)

                return result

        except Exception as e:
            logger.error(f"Content routing failed: {e}")
            processing_time = max((time.time() - start_time) * 1000, 0.1)
            return RoutingResult(
                content_id=content.content_id,
                processing_time_ms=processing_time,
                success=False,
                error_message=str(e),
            )

    def _generate_cache_key(
        self,
        content: RoutingContent,
        user_id: str | None,
    ) -> str:
        """Generate cache key for routing decision"""
        key_data = f"{content.content_id}_{content.quality_score}_{
            content.urgency_score
        }_{user_id or 'anonymous'}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def _apply_load_balancing(
        self,
        decisions: list[RoutingDecision],
        user_context: UserContext,
    ) -> list[RoutingDecision]:
        """Apply load balancing to routing decisions"""
        if not self.load_balancer.check_user_capacity(user_context.user_id):
            # User at capacity, defer or archive content
            for decision in decisions:
                if decision.routing_priority == RoutingPriority.URGENT:
                    continue  # Don't defer urgent content

                # Convert to deferred priority and increase delay
                deferred_decision = RoutingDecision(
                    content_id=decision.content_id,
                    destination=decision.destination,
                    routing_priority=RoutingPriority.DEFERRED,
                    reasoning=decision.reasoning + ["Load balancing: user at capacity"],
                    confidence_score=decision.confidence_score,
                    processing_delay_ms=decision.processing_delay_ms
                    + 3600000,  # Add 1 hour delay
                    metadata=decision.metadata,
                )
                decisions = [
                    deferred_decision if d == decision else d for d in decisions
                ]

            self.metrics["load_balancing_applied"] += 1

        return decisions

    def _apply_intelligent_delays(
        self,
        decisions: list[RoutingDecision],
        content: RoutingContent,
    ) -> list[RoutingDecision]:
        """Apply intelligent delays based on content characteristics"""
        modified_decisions = []

        for decision in decisions:
            # Calculate optimal delay based on content type and destination
            optimal_delay = self._calculate_optimal_delay(content, decision.destination)

            if optimal_delay > decision.processing_delay_ms:
                delayed_decision = RoutingDecision(
                    content_id=decision.content_id,
                    destination=decision.destination,
                    routing_priority=decision.routing_priority,
                    reasoning=decision.reasoning
                    + [f"Intelligent delay applied: {optimal_delay}ms"],
                    confidence_score=decision.confidence_score,
                    processing_delay_ms=optimal_delay,
                    metadata=decision.metadata,
                )
                modified_decisions.append(delayed_decision)
                self.metrics["intelligent_delays_applied"] += 1
            else:
                modified_decisions.append(decision)

        return modified_decisions

    def _calculate_optimal_delay(
        self,
        content: RoutingContent,
        destination: ContentDestination,
    ) -> int:
        """Calculate optimal delivery delay"""
        base_delay = 0

        # Email digest gets longer delays for batching
        if destination == ContentDestination.EMAIL_DIGEST:
            base_delay = 1800000  # 30 minutes

        # Research papers can wait longer
        if content.category == ContentCategory.RESEARCH_PAPER:
            base_delay = max(base_delay, 900000)  # 15 minutes

        # Entertainment content can be delayed more during work hours
        if content.category == ContentCategory.ENTERTAINMENT:
            current_hour = datetime.now(UTC).hour
            if 9 <= current_hour <= 17:  # Work hours
                base_delay = max(base_delay, 7200000)  # 2 hours

        return min(base_delay, self.config.max_processing_delay_minutes * 60000)

    async def batch_route_content(
        self,
        content_items: list[RoutingContent],
        user_id: str | None = None,
    ) -> list[RoutingResult]:
        """Route multiple content items efficiently"""
        if len(content_items) >= self.config.batch_processing_threshold:
            # Use batch processing for large volumes
            return await self._batch_process_routing(content_items, user_id)
        # Process individually for smaller volumes
        tasks = [self.route_content(content, user_id) for content in content_items]
        return await asyncio.gather(*tasks)

    async def _batch_process_routing(
        self,
        content_items: list[RoutingContent],
        user_id: str | None,
    ) -> list[RoutingResult]:
        """Optimized batch processing for large content volumes"""
        results = []

        # Group content by category for optimized processing
        categorized_content = defaultdict(list)
        for content in content_items:
            categorized_content[content.category].append(content)

        # Process each category efficiently
        for category, category_content in categorized_content.items():
            batch_results = await asyncio.gather(
                *[self.route_content(content, user_id) for content in category_content],
            )
            results.extend(batch_results)

        return results

    def get_metrics(self) -> dict[str, Any]:
        """Get routing engine metrics"""
        return {
            **self.metrics,
            "cached_routing_decisions": len(self.routing_cache),
            "active_user_contexts": len(self.user_contexts),
            "active_routing_rules": len(
                [r for r in self.intelligent_router.routing_rules if r.is_active],
            ),
            "average_processing_time_ms": self._calculate_average_processing_time(),
        }

    def _calculate_average_processing_time(self) -> float:
        """Calculate average processing time from cached results"""
        if not self.routing_cache:
            return 0.0

        total_time = sum(
            result.processing_time_ms for result, _ in self.routing_cache.values()
        )
        return total_time / len(self.routing_cache)


def create_production_content_routing_engine() -> ContentRoutingEngine:
    """Factory function to create production-optimized content routing engine"""
    config = ContentRoutingConfig(
        default_routing_strategy=RoutingStrategy.INTELLIGENT_HYBRID,
        max_routing_destinations=5,  # More routing options
        quality_threshold_high=0.85,  # Higher quality thresholds
        quality_threshold_medium=0.7,
        urgency_threshold_urgent=0.95,  # More selective urgency
        urgency_threshold_high=0.8,
        max_user_content_per_hour=25,  # Lower content volume per user
        enable_load_balancing=True,
        enable_intelligent_delays=True,
        max_processing_delay_minutes=120,  # Longer maximum delays
        batch_processing_threshold=50,  # Lower batch threshold
        cache_routing_decisions=True,
        routing_cache_ttl_minutes=3,  # Shorter cache for dynamic routing
        max_concurrent_routing=50,  # Higher concurrency
        enable_feedback_learning=True,
    )

    return ContentRoutingEngine(config)
