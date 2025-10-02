#!/usr/bin/env python3
"""PAKE System - Shared Utilities and Common Logic
Extracted shared functionality to break circular dependencies.
"""

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Callable

logger = logging.getLogger(__name__)


def generate_cache_key(data: Dict[str, Any], prefix: str = "") -> str:
    """Generate deterministic cache key from data dictionary"""
    cache_string = json.dumps(data, sort_keys=True)
    hash_digest = hashlib.sha256(cache_string.encode()).hexdigest()[:16]
    return f"{prefix}_{hash_digest}" if prefix else hash_digest


def extract_search_terms(topic: str) -> List[str]:
    """Extract relevant search terms from research topic"""
    # Simple term extraction - can be enhanced with NLP
    terms = []

    # Split and clean topic
    words = topic.lower().replace("-", " ").split()

    # Filter out common words and create meaningful terms
    stopwords = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"
    }
    meaningful_words = [
        word for word in words if word not in stopwords and len(word) > 2
    ]

    # Add individual terms
    terms.extend(meaningful_words)

    # Add key phrases
    if len(meaningful_words) >= 2:
        terms.append(" ".join(meaningful_words[:2]))

    return terms[:5]  # Limit to top 5 terms


def extract_research_domain(topic: str) -> str | None:
    """Extract research domain from topic for workflow routing"""
    topic_lower = topic.lower()

    # Medical/Biomedical domain
    biomedical_keywords = [
        "biomedical", "medical", "clinical", "health", "medicine", "biological",
        "bio", "disease", "treatment", "drug", "pharmaceutical", "therapeutic", "diagnostic"
    ]

    if any(keyword in topic_lower for keyword in biomedical_keywords):
        return "biomedical"

    # Technology/AI domain
    tech_keywords = [
        "ai", "artificial intelligence", "machine learning", "deep learning",
        "technology", "computing", "software", "algorithm", "automation"
    ]

    if any(keyword in topic_lower for keyword in tech_keywords):
        return "technology"

    # Financial domain
    finance_keywords = [
        "financial", "finance", "economic", "market", "investment", "trading",
        "banking", "cryptocurrency", "fintech"
    ]

    if any(keyword in topic_lower for keyword in finance_keywords):
        return "financial"

    # Environmental domain
    environmental_keywords = [
        "environmental", "climate", "sustainability", "green", "ecology",
        "conservation", "renewable", "carbon"
    ]

    if any(keyword in topic_lower for keyword in environmental_keywords):
        return "environmental"

    return None  # Generic processing if no specific domain detected


def calculate_duration_estimate(sources: List[Dict[str, Any]]) -> int:
    """Calculate estimated total duration for all sources"""
    # Base duration per source type (seconds)
    duration_map = {
        "web": 30,
        "arxiv": 45,
        "pubmed": 60,
        "rss": 20,
        "email": 15,
        "social": 25,
    }

    total_duration = 0
    for source in sources:
        source_type = source.get("source_type", "web")
        estimated_results = source.get("estimated_results", 10)
        
        base_duration = duration_map.get(source_type, 30)
        # Adjust based on estimated results
        adjusted_duration = base_duration + (estimated_results * 2)
        total_duration += adjusted_duration

    return total_duration


def validate_source_config(config: Dict[str, Any]) -> bool:
    """Validate source configuration"""
    required_fields = ["source_type", "query_parameters"]
    
    for field in required_fields:
        if field not in config:
            logger.error(f"Missing required field '{field}' in source config")
            return False
    
    if not config.get("query_parameters"):
        logger.error("Query parameters cannot be empty")
        return False
    
    if config.get("estimated_results", 0) <= 0:
        logger.error("Estimated results must be greater than 0")
        return False
    
    return True


def format_execution_metrics(
    execution_time: float,
    sources_completed: int,
    sources_failed: int,
    total_items: int,
) -> Dict[str, Any]:
    """Format execution metrics in a standardized way"""
    return {
        "execution_time_ms": execution_time * 1000,
        "sources_completed": sources_completed,
        "sources_failed": sources_failed,
        "total_items_retrieved": total_items,
        "success_rate": sources_completed / max(sources_completed + sources_failed, 1),
        "items_per_second": total_items / max(execution_time, 0.001),
        "timestamp": datetime.now(UTC).isoformat(),
    }


def create_error_detail(
    source_id: str,
    source_type: str,
    error: str,
    attempt: int = 0,
) -> Dict[str, Any]:
    """Create standardized error detail structure"""
    return {
        "source_id": source_id,
        "source_type": source_type,
        "error": str(error),
        "attempt": attempt,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def merge_content_items(items_list: List[List[Any]]) -> List[Any]:
    """Merge multiple lists of content items into a single list"""
    merged = []
    for items in items_list:
        if isinstance(items, list):
            merged.extend(items)
        else:
            merged.append(items)
    return merged


def deduplicate_by_key(
    items: List[Any],
    key_extractor: Callable[[Any], str],
) -> List[Any]:
    """Deduplicate items based on a key extraction function"""
    seen_keys = set()
    unique_items = []
    
    for item in items:
        key = key_extractor(item)
        if key not in seen_keys:
            seen_keys.add(key)
            unique_items.append(item)
    
    return unique_items
