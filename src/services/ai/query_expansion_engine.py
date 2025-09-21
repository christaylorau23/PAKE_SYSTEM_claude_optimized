#!/usr/bin/env python3
"""PAKE System - Intelligent Query Expansion Engine
Phase 3 Sprint 5: Advanced AI integration with query optimization and enhancement

Provides intelligent query expansion, synonym detection, context awareness,
and AI-powered search optimization for enhanced content discovery.
"""

import asyncio
import hashlib
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ExpansionStrategy(Enum):
    """Query expansion strategies"""

    SYNONYM_BASED = "synonym_based"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    CO_OCCURRENCE = "co_occurrence"
    CONTEXTUAL_EXPANSION = "contextual_expansion"
    HYBRID_EXPANSION = "hybrid_expansion"


class ExpansionScope(Enum):
    """Scope of query expansion"""

    CONSERVATIVE = "conservative"  # Add 1-2 related terms
    MODERATE = "moderate"  # Add 3-5 related terms
    AGGRESSIVE = "aggressive"  # Add 5+ related terms
    ADAPTIVE = "adaptive"  # Dynamically adjust based on results


class QueryType(Enum):
    """Types of search queries"""

    FACTUAL = "factual"  # What is X?
    PROCEDURAL = "procedural"  # How to do X?
    COMPARATIVE = "comparative"  # X vs Y
    EXPLORATORY = "exploratory"  # Tell me about X
    SPECIFIC = "specific"  # Find exact match
    BROAD = "broad"  # General topic search


@dataclass(frozen=True)
class ExpansionTerm:
    """Immutable expanded query term"""

    term: str
    confidence: float  # 0.0 to 1.0
    expansion_type: str
    source: str = ""
    weight: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "term": self.term,
            "confidence": self.confidence,
            "expansion_type": self.expansion_type,
            "source": self.source,
            "weight": self.weight,
        }


@dataclass(frozen=True)
class QueryAnalysis:
    """Immutable query analysis result"""

    original_query: str
    query_type: QueryType
    key_entities: list[str]
    intent_confidence: float
    complexity_score: float  # 0.0 to 1.0
    domain_hints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "original_query": self.original_query,
            "query_type": self.query_type.value,
            "key_entities": self.key_entities,
            "intent_confidence": self.intent_confidence,
            "complexity_score": self.complexity_score,
            "domain_hints": self.domain_hints,
        }


@dataclass(frozen=True)
class ExpandedQuery:
    """Immutable expanded query result"""

    original_query: str
    expanded_terms: list[ExpansionTerm]
    final_query: str
    expansion_strategy: ExpansionStrategy
    expansion_scope: ExpansionScope

    # Analysis metadata
    analysis: QueryAnalysis
    expansion_time_ms: float
    confidence_score: float

    # Performance hints
    suggested_filters: dict[str, Any] = field(default_factory=dict)
    boost_terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "original_query": self.original_query,
            "expanded_terms": [term.to_dict() for term in self.expanded_terms],
            "final_query": self.final_query,
            "expansion_strategy": self.expansion_strategy.value,
            "expansion_scope": self.expansion_scope.value,
            "analysis": self.analysis.to_dict(),
            "expansion_time_ms": self.expansion_time_ms,
            "confidence_score": self.confidence_score,
            "suggested_filters": self.suggested_filters,
            "boost_terms": self.boost_terms,
        }


@dataclass
class ExpansionConfig:
    """Configuration for query expansion engine"""

    # Expansion settings
    enable_synonym_expansion: bool = True
    enable_semantic_expansion: bool = True
    enable_contextual_expansion: bool = True
    enable_co_occurrence_expansion: bool = True

    # Scope settings
    default_expansion_scope: ExpansionScope = ExpansionScope.MODERATE
    max_expanded_terms: int = 10
    min_term_confidence: float = 0.3

    # Performance settings
    enable_expansion_caching: bool = True
    cache_ttl_seconds: int = 3600
    max_concurrent_expansions: int = 5
    expansion_timeout_ms: int = 1000

    # Quality settings
    synonym_confidence_threshold: float = 0.7
    semantic_similarity_threshold: float = 0.6
    co_occurrence_threshold: float = 0.5

    # Advanced features
    enable_query_intent_analysis: bool = True
    enable_domain_detection: bool = True
    enable_personalization: bool = False

    # Language settings
    supported_languages: list[str] = field(default_factory=lambda: ["en"])
    default_language: str = "en"


class QueryAnalyzer(ABC):
    """Abstract base for query analysis implementations"""

    @abstractmethod
    async def analyze_query(
        self,
        query: str,
        context: dict[str, Any] = None,
    ) -> QueryAnalysis:
        """Analyze query intent and structure"""


class SimpleQueryAnalyzer(QueryAnalyzer):
    """Simple rule-based query analyzer"""

    def __init__(self, config: ExpansionConfig):
        self.config = config

        # Query type patterns
        self.query_patterns = {
            QueryType.FACTUAL: {
                r"\bwhat\s+is\b",
                r"\bwhat\s+are\b",
                r"\bdefine\b",
                r"\bdefinition\b",
                r"\bexplain\b",
                r"\bmean\b",
                r"\bmeaning\b",
            },
            QueryType.PROCEDURAL: {
                r"\bhow\s+to\b",
                r"\bhow\s+do\b",
                r"\bhow\s+can\b",
                r"\bsteps\b",
                r"\bguide\b",
                r"\btutorial\b",
                r"\bprocess\b",
            },
            QueryType.COMPARATIVE: {
                r"\bvs\b",
                r"\bversus\b",
                r"\bcompare\b",
                r"\bdifference\b",
                r"\bbetter\b",
                r"\bbest\b",
                r"\bworst\b",
            },
            QueryType.EXPLORATORY: {
                r"\btell\s+me\b",
                r"\blearn\s+about\b",
                r"\binformation\b",
                r"\babout\b",
                r"\boverview\b",
                r"\bintroduction\b",
            },
        }

        # Domain indicators
        self.domain_keywords = {
            "technology": {
                "software",
                "programming",
                "algorithm",
                "computer",
                "digital",
                "ai",
                "machine learning",
                "data science",
            },
            "science": {
                "research",
                "study",
                "experiment",
                "hypothesis",
                "theory",
                "analysis",
                "scientific",
                "laboratory",
            },
            "business": {
                "company",
                "market",
                "strategy",
                "revenue",
                "profit",
                "management",
                "enterprise",
                "corporate",
            },
            "healthcare": {
                "medical",
                "health",
                "treatment",
                "patient",
                "clinical",
                "therapy",
                "medicine",
                "disease",
            },
        }

    async def analyze_query(
        self,
        query: str,
        context: dict[str, Any] = None,
    ) -> QueryAnalysis:
        """Analyze query to determine intent and characteristics"""
        query_lower = query.lower()

        # Determine query type
        query_type = QueryType.SPECIFIC  # Default
        max_confidence = 0.0

        for qtype, patterns in self.query_patterns.items():
            confidence = 0.0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    confidence = 0.8
                    break

            if confidence > max_confidence:
                max_confidence = confidence
                query_type = qtype

        # If no specific pattern found, determine based on length and structure
        if max_confidence == 0.0:
            words = len(query.split())
            if words > 10:
                query_type = QueryType.EXPLORATORY
                max_confidence = 0.6
            elif words > 5:
                query_type = QueryType.BROAD
                max_confidence = 0.5
            else:
                max_confidence = 0.4

        # Extract key entities (simple approach - proper nouns and important terms)
        key_entities = self._extract_entities(query)

        # Calculate complexity score
        # Normalize by typical query length
        complexity_score = min(1.0, len(query.split()) / 20.0)

        # Detect domain hints
        domain_hints = self._detect_domains(query_lower)

        return QueryAnalysis(
            original_query=query,
            query_type=query_type,
            key_entities=key_entities,
            intent_confidence=max_confidence,
            complexity_score=complexity_score,
            domain_hints=domain_hints,
        )

    def _extract_entities(self, query: str) -> list[str]:
        """Extract key entities from query"""
        # Simple entity extraction - capitalize words and technical terms
        entities = []
        words = query.split()

        for word in words:
            # Skip common stop words
            if word.lower() in {
                "the",
                "a",
                "an",
                "and",
                "or",
                "but",
                "in",
                "on",
                "at",
                "to",
                "for",
                "of",
                "with",
                "by",
            }:
                continue

            # Keep words that are capitalized or look technical
            if (
                word[0].isupper()
                or len(word) > 6
                or any(char.isdigit() for char in word)
            ):
                entities.append(word)

        return entities[:10]  # Limit to top 10

    def _detect_domains(self, query: str) -> list[str]:
        """Detect domain hints from query content"""
        detected_domains = []

        for domain, keywords in self.domain_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in query:
                    score += 1

            if score > 0:
                detected_domains.append(domain)

        return detected_domains


class ExpansionTermGenerator(ABC):
    """Abstract base for term expansion implementations"""

    @abstractmethod
    async def generate_expansions(
        self,
        query: str,
        analysis: QueryAnalysis,
        context: dict[str, Any] = None,
    ) -> list[ExpansionTerm]:
        """Generate expansion terms for query"""


class SynonymExpander(ExpansionTermGenerator):
    """Synonym-based query expansion"""

    def __init__(self, config: ExpansionConfig):
        self.config = config

        # Pre-built synonym dictionary (in production, this would be more comprehensive)
        self.synonym_dict = {
            # Technology synonyms
            "computer": ["machine", "system", "device", "pc"],
            "software": ["program", "application", "app", "tool"],
            "algorithm": ["method", "procedure", "process", "technique"],
            "artificial intelligence": [
                "ai",
                "machine learning",
                "ml",
                "deep learning",
            ],
            "machine learning": ["ml", "ai", "artificial intelligence", "data science"],
            "data science": [
                "analytics",
                "data analysis",
                "machine learning",
                "statistics",
            ],
            # Research synonyms
            "research": ["study", "investigation", "analysis", "examination"],
            "study": ["research", "analysis", "investigation", "review"],
            "method": ["approach", "technique", "procedure", "process"],
            "analysis": ["examination", "evaluation", "assessment", "review"],
            # Business synonyms
            "company": ["business", "corporation", "firm", "enterprise"],
            "strategy": ["plan", "approach", "method", "tactic"],
            "market": ["industry", "sector", "marketplace", "economy"],
            # General synonyms
            "improve": ["enhance", "optimize", "better", "upgrade"],
            "problem": ["issue", "challenge", "difficulty", "obstacle"],
            "solution": ["answer", "resolution", "fix", "remedy"],
        }

    async def generate_expansions(
        self,
        query: str,
        analysis: QueryAnalysis,
        context: dict[str, Any] = None,
    ) -> list[ExpansionTerm]:
        """Generate synonym-based expansion terms"""
        expansions = []
        query_lower = query.lower()

        # Look for exact matches in synonym dictionary
        for term, synonyms in self.synonym_dict.items():
            if term in query_lower:
                for synonym in synonyms[:3]:  # Limit to top 3 synonyms
                    if synonym not in query_lower:  # Avoid duplicates
                        expansion = ExpansionTerm(
                            term=synonym,
                            confidence=0.8,
                            expansion_type="synonym",
                            source="synonym_dict",
                            weight=0.9,
                        )
                        expansions.append(expansion)

        # Also look for individual words that might have synonyms
        words = [word.strip('.,!?;:"()[]') for word in query.split()]
        for word in words:
            word_lower = word.lower()
            if word_lower in self.synonym_dict:
                for synonym in self.synonym_dict[word_lower][:2]:
                    if synonym not in query_lower:
                        expansion = ExpansionTerm(
                            term=synonym,
                            confidence=0.7,
                            expansion_type="word_synonym",
                            source="synonym_dict",
                            weight=0.8,
                        )
                        expansions.append(expansion)

        # Sort by confidence and return top terms
        expansions.sort(key=lambda x: x.confidence, reverse=True)
        return expansions[: self.config.max_expanded_terms // 2]


class SemanticExpander(ExpansionTermGenerator):
    """Semantic similarity-based query expansion"""

    def __init__(self, config: ExpansionConfig):
        self.config = config

        # Semantic relationships (simplified - in production would use word embeddings)
        self.semantic_clusters = {
            "machine_learning": {
                "neural networks",
                "deep learning",
                "supervised learning",
                "unsupervised learning",
                "classification",
                "regression",
                "clustering",
                "feature engineering",
            },
            "data_science": {
                "statistics",
                "data analysis",
                "data mining",
                "predictive modeling",
                "visualization",
                "big data",
                "python",
                "r programming",
            },
            "web_development": {
                "javascript",
                "html",
                "css",
                "react",
                "node.js",
                "frontend",
                "backend",
                "full stack",
                "api",
                "database",
            },
            "artificial_intelligence": {
                "machine learning",
                "natural language processing",
                "computer vision",
                "robotics",
                "expert systems",
                "neural networks",
            },
            "research_methodology": {
                "experimental design",
                "statistical analysis",
                "hypothesis testing",
                "data collection",
                "literature review",
                "peer review",
            },
        }

    async def generate_expansions(
        self,
        query: str,
        analysis: QueryAnalysis,
        context: dict[str, Any] = None,
    ) -> list[ExpansionTerm]:
        """Generate semantically related expansion terms"""
        expansions = []
        query_lower = query.lower()

        # Find semantic clusters that match the query
        for cluster_name, related_terms in self.semantic_clusters.items():
            cluster_match_score = 0
            matched_terms = []

            # Check if query contains terms from this cluster
            for term in related_terms:
                if term in query_lower:
                    cluster_match_score += 1
                    matched_terms.append(term)

            # If cluster is relevant, add related terms
            if cluster_match_score > 0:
                confidence = min(0.9, cluster_match_score / len(related_terms) + 0.3)

                for term in related_terms:
                    if term not in query_lower and term not in matched_terms:
                        expansion = ExpansionTerm(
                            term=term,
                            confidence=confidence,
                            expansion_type="semantic",
                            source=f"cluster_{cluster_name}",
                            weight=0.85,
                        )
                        expansions.append(expansion)

        # Also look for domain-specific expansions based on analysis
        for domain in analysis.domain_hints:
            domain_terms = self._get_domain_terms(domain)
            for term in domain_terms[:3]:
                if term not in query_lower:
                    expansion = ExpansionTerm(
                        term=term,
                        confidence=0.6,
                        expansion_type="domain_semantic",
                        source=f"domain_{domain}",
                        weight=0.7,
                    )
                    expansions.append(expansion)

        # Sort by confidence and return top terms
        expansions.sort(key=lambda x: x.confidence, reverse=True)
        return expansions[: self.config.max_expanded_terms // 2]

    def _get_domain_terms(self, domain: str) -> list[str]:
        """Get relevant terms for a specific domain"""
        domain_specific_terms = {
            "technology": [
                "innovation",
                "digital transformation",
                "automation",
                "scalability",
            ],
            "science": ["methodology", "empirical", "hypothesis", "peer review"],
            "business": ["ROI", "KPI", "stakeholder", "market analysis"],
            "healthcare": [
                "clinical trial",
                "patient care",
                "medical device",
                "healthcare delivery",
            ],
        }

        return domain_specific_terms.get(domain, [])


class ContextualExpander(ExpansionTermGenerator):
    """Context-aware query expansion"""

    def __init__(self, config: ExpansionConfig):
        self.config = config

        # Contextual patterns for different query types
        self.contextual_patterns = {
            QueryType.PROCEDURAL: {
                "terms": [
                    "tutorial",
                    "guide",
                    "step-by-step",
                    "instructions",
                    "how-to",
                ],
                "boost": ["process", "method", "technique"],
            },
            QueryType.FACTUAL: {
                "terms": ["definition", "explanation", "overview", "introduction"],
                "boost": ["concept", "theory", "principle"],
            },
            QueryType.COMPARATIVE: {
                "terms": ["comparison", "versus", "pros and cons", "advantages"],
                "boost": ["evaluation", "assessment", "analysis"],
            },
            QueryType.EXPLORATORY: {
                "terms": ["comprehensive", "detailed", "in-depth", "extensive"],
                "boost": ["research", "study", "investigation"],
            },
        }

    async def generate_expansions(
        self,
        query: str,
        analysis: QueryAnalysis,
        context: dict[str, Any] = None,
    ) -> list[ExpansionTerm]:
        """Generate context-aware expansion terms"""
        expansions = []

        # Get contextual terms based on query type
        if analysis.query_type in self.contextual_patterns:
            pattern_info = self.contextual_patterns[analysis.query_type]

            # Add contextual terms
            for term in pattern_info.get("terms", []):
                if term not in query.lower():
                    expansion = ExpansionTerm(
                        term=term,
                        confidence=0.7,
                        expansion_type="contextual",
                        source=f"context_{analysis.query_type.value}",
                        weight=0.8,
                    )
                    expansions.append(expansion)

            # Add boost terms
            for term in pattern_info.get("boost", []):
                if term not in query.lower():
                    expansion = ExpansionTerm(
                        term=term,
                        confidence=0.6,
                        expansion_type="contextual_boost",
                        source=f"boost_{analysis.query_type.value}",
                        weight=1.2,  # Higher weight for boost terms
                    )
                    expansions.append(expansion)

        # Add complexity-based expansions
        if analysis.complexity_score > 0.7:  # Complex query
            complex_terms = ["comprehensive", "detailed", "advanced", "in-depth"]
            for term in complex_terms[:2]:
                if term not in query.lower():
                    expansion = ExpansionTerm(
                        term=term,
                        confidence=0.5,
                        expansion_type="complexity",
                        source="complexity_analysis",
                        weight=0.9,
                    )
                    expansions.append(expansion)

        return expansions[: self.config.max_expanded_terms // 3]


class QueryExpansionEngine:
    """Intelligent query expansion engine with AI-powered optimization.
    Provides synonym detection, semantic expansion, and contextual enhancement.
    """

    def __init__(self, config: ExpansionConfig = None):
        self.config = config or ExpansionConfig()

        # Initialize components
        self.query_analyzer = SimpleQueryAnalyzer(self.config)

        # Initialize expanders
        self.expanders = []
        if self.config.enable_synonym_expansion:
            self.expanders.append(SynonymExpander(self.config))
        if self.config.enable_semantic_expansion:
            self.expanders.append(SemanticExpander(self.config))
        if self.config.enable_contextual_expansion:
            self.expanders.append(ContextualExpander(self.config))

        # Caching
        self.expansion_cache: dict[str, ExpandedQuery] = {}

        # Statistics
        self.stats = {
            "total_expansions": 0,
            "cache_hits": 0,
            "average_expansion_time": 0.0,
            "expansion_success_rate": 0.0,
        }

        logger.info("Initialized Query Expansion Engine")

    def _generate_cache_key(
        self,
        query: str,
        expansion_strategy: ExpansionStrategy = None,
        expansion_scope: ExpansionScope = None,
        context: dict[str, Any] = None,
    ) -> str:
        """Generate cache key for query expansion"""
        cache_data = {"query": query.lower().strip()}

        # Include strategy and scope in cache key
        if expansion_strategy:
            cache_data["strategy"] = expansion_strategy.value
        if expansion_scope:
            cache_data["scope"] = expansion_scope.value

        if context:
            # Include stable context elements
            stable_context = {
                key: value
                for key, value in context.items()
                if key in ["domain", "user_type", "language"]
                and isinstance(value, (str, int, float, bool))
            }
            if stable_context:
                cache_data["context"] = stable_context

        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_str.encode()).hexdigest()[:16]

    async def expand_query(
        self,
        query: str,
        expansion_strategy: ExpansionStrategy = None,
        expansion_scope: ExpansionScope = None,
        context: dict[str, Any] = None,
    ) -> ExpandedQuery:
        """Expand query with intelligent term suggestions and optimization."""
        start_time = time.time()

        try:
            # Use defaults if not specified
            expansion_strategy = (
                expansion_strategy or ExpansionStrategy.HYBRID_EXPANSION
            )
            expansion_scope = expansion_scope or self.config.default_expansion_scope
            context = context or {}

            # Check cache (after setting defaults)
            cache_key = self._generate_cache_key(
                query,
                expansion_strategy,
                expansion_scope,
                context,
            )
            if (
                self.config.enable_expansion_caching
                and cache_key in self.expansion_cache
            ):
                self.stats["cache_hits"] += 1
                return self.expansion_cache[cache_key]

            # Analyze query
            analysis = await self.query_analyzer.analyze_query(query, context)

            # Generate expansions using appropriate expanders
            all_expansions = []

            for expander in self.expanders:
                try:
                    expansions = await expander.generate_expansions(
                        query,
                        analysis,
                        context,
                    )
                    all_expansions.extend(expansions)
                except Exception as e:
                    logger.warning(
                        f"Expander {expander.__class__.__name__} failed: {e}",
                    )

            # Filter and rank expansions
            filtered_expansions = self._filter_and_rank_expansions(
                all_expansions,
                expansion_scope,
                analysis,
            )

            # Build final expanded query
            final_query = self._build_final_query(
                query,
                filtered_expansions,
                expansion_strategy,
            )

            # Calculate confidence and performance metrics
            expansion_time = max(
                0.1,
                (time.time() - start_time) * 1000,
            )  # Ensure minimum time
            confidence_score = self._calculate_expansion_confidence(
                filtered_expansions,
                analysis,
            )

            # Generate performance hints
            suggested_filters, boost_terms = self._generate_performance_hints(
                filtered_expansions,
                analysis,
            )

            expanded_query = ExpandedQuery(
                original_query=query,
                expanded_terms=filtered_expansions,
                final_query=final_query,
                expansion_strategy=expansion_strategy,
                expansion_scope=expansion_scope,
                analysis=analysis,
                expansion_time_ms=expansion_time,
                confidence_score=confidence_score,
                suggested_filters=suggested_filters,
                boost_terms=boost_terms,
            )

            # Cache result
            if self.config.enable_expansion_caching:
                self.expansion_cache[cache_key] = expanded_query
                # Simple cache management
                if len(self.expansion_cache) > 1000:
                    oldest_keys = list(self.expansion_cache.keys())[:100]
                    for old_key in oldest_keys:
                        del self.expansion_cache[old_key]

            # Update statistics
            self.stats["total_expansions"] += 1

            return expanded_query

        except Exception as e:
            logger.error(f"Query expansion failed for '{query}': {e}")
            # Return minimal expansion on error
            return self._create_minimal_expansion(query, start_time, str(e))

    def _filter_and_rank_expansions(
        self,
        expansions: list[ExpansionTerm],
        scope: ExpansionScope,
        analysis: QueryAnalysis,
    ) -> list[ExpansionTerm]:
        """Filter and rank expansion terms based on scope and quality"""
        # Remove duplicates
        unique_expansions = {}
        for expansion in expansions:
            key = expansion.term.lower()
            if (
                key not in unique_expansions
                or expansion.confidence > unique_expansions[key].confidence
            ):
                unique_expansions[key] = expansion

        filtered = list(unique_expansions.values())

        # Filter by confidence threshold
        filtered = [
            exp for exp in filtered if exp.confidence >= self.config.min_term_confidence
        ]

        # Sort by confidence and weight
        filtered.sort(key=lambda x: x.confidence * x.weight, reverse=True)

        # Apply scope limits
        scope_limits = {
            ExpansionScope.CONSERVATIVE: 2,
            ExpansionScope.MODERATE: 5,
            ExpansionScope.AGGRESSIVE: 10,
            ExpansionScope.ADAPTIVE: min(
                10,
                max(2, int(analysis.complexity_score * 8)),
            ),
        }

        limit = scope_limits.get(scope, 5)
        return filtered[:limit]

    def _build_final_query(
        self,
        original_query: str,
        expansions: list[ExpansionTerm],
        strategy: ExpansionStrategy,
    ) -> str:
        """Build final expanded query string"""
        if not expansions:
            return original_query

        # Extract expansion terms
        expansion_terms = [exp.term for exp in expansions]

        if strategy == ExpansionStrategy.SYNONYM_BASED:
            # Add synonyms with OR logic
            synonym_terms = [
                exp.term
                for exp in expansions
                if exp.expansion_type in ["synonym", "word_synonym"]
            ]
            if synonym_terms:
                return f"{original_query} {' '.join(synonym_terms)}"

        elif strategy == ExpansionStrategy.SEMANTIC_SIMILARITY:
            # Add semantic terms
            semantic_terms = [
                exp.term for exp in expansions if exp.expansion_type == "semantic"
            ]
            if semantic_terms:
                return f"{original_query} {' '.join(semantic_terms[:3])}"

        elif strategy == ExpansionStrategy.CONTEXTUAL_EXPANSION:
            # Add contextual terms
            contextual_terms = [
                exp.term for exp in expansions if "contextual" in exp.expansion_type
            ]
            if contextual_terms:
                return f"{original_query} {' '.join(contextual_terms[:2])}"

        # Default hybrid approach - mix all types
        high_confidence_terms = [exp.term for exp in expansions if exp.confidence > 0.7]
        if high_confidence_terms:
            return f"{original_query} {' '.join(high_confidence_terms[:4])}"
        return f"{original_query} {' '.join(expansion_terms[:3])}"

    def _calculate_expansion_confidence(
        self,
        expansions: list[ExpansionTerm],
        analysis: QueryAnalysis,
    ) -> float:
        """Calculate overall confidence in the expansion"""
        if not expansions:
            return 0.0

        # Average confidence of expansions
        avg_confidence = sum(exp.confidence for exp in expansions) / len(expansions)

        # Boost confidence based on query analysis
        analysis_boost = analysis.intent_confidence * 0.2

        # Penalize if too few expansions found
        expansion_penalty = 0.0 if len(expansions) >= 3 else 0.1

        final_confidence = min(1.0, avg_confidence + analysis_boost - expansion_penalty)
        return final_confidence

    def _generate_performance_hints(
        self,
        expansions: list[ExpansionTerm],
        analysis: QueryAnalysis,
    ) -> tuple[dict[str, Any], list[str]]:
        """Generate performance optimization hints"""
        suggested_filters = {}
        boost_terms = []

        # Suggest filters based on domain hints
        for domain in analysis.domain_hints:
            suggested_filters[f"domain_{domain}"] = True

        # Suggest filters based on query type
        if analysis.query_type == QueryType.PROCEDURAL:
            suggested_filters["content_type"] = ["tutorial", "guide", "howto"]
        elif analysis.query_type == QueryType.FACTUAL:
            suggested_filters["content_type"] = [
                "definition",
                "explanation",
                "reference",
            ]

        # Extract boost terms from high-weight expansions
        boost_terms = [
            exp.term
            for exp in expansions
            if exp.weight > 1.0 or exp.expansion_type == "contextual_boost"
        ]

        return suggested_filters, boost_terms[:5]

    def _create_minimal_expansion(
        self,
        query: str,
        start_time: float,
        error_msg: str = None,
    ) -> ExpandedQuery:
        """Create minimal expansion for error cases"""
        expansion_time = max(
            0.1,
            (time.time() - start_time) * 1000,
        )  # Ensure minimum time

        # Create basic analysis
        analysis = QueryAnalysis(
            original_query=query,
            query_type=QueryType.SPECIFIC,
            key_entities=[],
            intent_confidence=0.0,
            complexity_score=0.0,
        )

        return ExpandedQuery(
            original_query=query,
            expanded_terms=[],
            final_query=query,
            expansion_strategy=ExpansionStrategy.HYBRID_EXPANSION,
            expansion_scope=ExpansionScope.CONSERVATIVE,
            analysis=analysis,
            expansion_time_ms=expansion_time,
            confidence_score=0.0,
        )

    def get_expansion_statistics(self) -> dict[str, Any]:
        """Get query expansion engine statistics"""
        stats = self.stats.copy()

        if stats["total_expansions"] > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / stats["total_expansions"]
        else:
            stats["cache_hit_rate"] = 0.0

        stats["cached_expansions"] = len(self.expansion_cache)
        stats["active_expanders"] = len(self.expanders)

        return stats

    async def clear_cache(self):
        """Clear expansion cache"""
        self.expansion_cache.clear()
        logger.info("Query expansion cache cleared")


# Production-ready factory functions
async def create_production_query_expansion_engine() -> QueryExpansionEngine:
    """Create production-ready query expansion engine"""
    config = ExpansionConfig(
        enable_synonym_expansion=True,
        enable_semantic_expansion=True,
        enable_contextual_expansion=True,
        enable_co_occurrence_expansion=True,
        default_expansion_scope=ExpansionScope.ADAPTIVE,
        max_expanded_terms=15,
        min_term_confidence=0.4,
        enable_expansion_caching=True,
        cache_ttl_seconds=7200,  # 2 hours
        max_concurrent_expansions=10,
        expansion_timeout_ms=2000,
        synonym_confidence_threshold=0.8,
        semantic_similarity_threshold=0.7,
        enable_query_intent_analysis=True,
        enable_domain_detection=True,
    )

    return QueryExpansionEngine(config)


if __name__ == "__main__":
    # Example usage
    async def main():
        engine = QueryExpansionEngine()

        # Test queries
        test_queries = [
            "machine learning algorithms",
            "how to build neural networks",
            "what is artificial intelligence",
            "compare deep learning vs traditional ML",
            "python programming tutorial",
        ]

        for query in test_queries:
            print(f"\nOriginal Query: {query}")

            expanded = await engine.expand_query(
                query,
                expansion_strategy=ExpansionStrategy.HYBRID_EXPANSION,
                expansion_scope=ExpansionScope.MODERATE,
            )

            print(f"Expanded Query: {expanded.final_query}")
            print(f"Query Type: {expanded.analysis.query_type.value}")
            print(f"Confidence: {expanded.confidence_score:.2f}")
            print(f"Expansion Terms: {[t.term for t in expanded.expanded_terms]}")
            print(f"Expansion Time: {expanded.expansion_time_ms:.1f}ms")

        stats = engine.get_expansion_statistics()
        print(f"\nExpansion Statistics: {stats}")

    asyncio.run(main())
