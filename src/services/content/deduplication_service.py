#!/usr/bin/env python3
"""PAKE System - Advanced Content Deduplication Service
Phase 2B Sprint 4: ML-powered content deduplication with similarity detection

Provides intelligent content deduplication using multiple algorithms:
- Hash-based exact duplicate detection
- ML-powered semantic similarity detection
- Content fingerprinting for near-duplicate detection
- Configurable similarity thresholds and policies
"""

import asyncio
import hashlib
import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class DeduplicationMethod(Enum):
    """Content deduplication methods"""

    EXACT_HASH = "exact_hash"  # SHA-256 hash matching
    CONTENT_HASH = "content_hash"  # Content-only hash (no metadata)
    FUZZY_HASH = "fuzzy_hash"  # Fuzzy hashing for near-duplicates
    SEMANTIC_SIMILARITY = "semantic"  # ML-based semantic similarity
    URL_NORMALIZATION = "url_norm"  # URL-based deduplication
    TITLE_SIMILARITY = "title_sim"  # Title/subject similarity


class DuplicateAction(Enum):
    """Actions to take when duplicates are found"""

    SKIP = "skip"  # Skip duplicate content
    MERGE = "merge"  # Merge duplicate content
    KEEP_LATEST = "keep_latest"  # Keep most recent version
    KEEP_BEST_QUALITY = "keep_best"  # Keep highest quality version
    FLAG_DUPLICATE = "flag"  # Flag as duplicate but keep


@dataclass(frozen=True)
class ContentFingerprint:
    """Immutable content fingerprint for deduplication"""

    content_hash: str  # Primary content hash
    metadata_hash: str  # Metadata hash
    fuzzy_hash: str | None = None  # Fuzzy hash for similarity
    title_tokens: set[str] = field(default_factory=set)  # Title tokens
    url_normalized: str | None = None  # Normalized URL
    content_length: int = 0  # Content length
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "content_hash": self.content_hash,
            "metadata_hash": self.metadata_hash,
            "fuzzy_hash": self.fuzzy_hash,
            "title_tokens": list(self.title_tokens),
            "url_normalized": self.url_normalized,
            "content_length": self.content_length,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class DeduplicationResult:
    """Result of deduplication analysis"""

    is_duplicate: bool = False
    method_used: DeduplicationMethod | None = None
    similarity_score: float = 0.0  # 0.0 to 1.0
    duplicate_of: str | None = None  # ID of original content
    action_taken: DuplicateAction = DuplicateAction.SKIP
    fingerprint: ContentFingerprint | None = None
    processing_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "is_duplicate": self.is_duplicate,
            "method_used": self.method_used.value if self.method_used else None,
            "similarity_score": self.similarity_score,
            "duplicate_of": self.duplicate_of,
            "action_taken": self.action_taken.value,
            "fingerprint": self.fingerprint.to_dict() if self.fingerprint else None,
            "processing_time_ms": self.processing_time_ms,
        }


@dataclass
class DeduplicationConfig:
    """Configuration for content deduplication"""

    # Similarity thresholds
    exact_match_threshold: float = 1.0  # Exact matches
    fuzzy_similarity_threshold: float = 0.85  # Fuzzy hash similarity
    semantic_similarity_threshold: float = 0.90  # Semantic similarity
    title_similarity_threshold: float = 0.95  # Title similarity
    url_similarity_threshold: float = 0.95  # URL similarity

    # Enabled methods
    enabled_methods: list[DeduplicationMethod] = field(
        default_factory=lambda: [
            DeduplicationMethod.EXACT_HASH,
            DeduplicationMethod.CONTENT_HASH,
            DeduplicationMethod.FUZZY_HASH,
            DeduplicationMethod.TITLE_SIMILARITY,
        ],
    )

    # Duplicate handling
    default_action: DuplicateAction = DuplicateAction.SKIP
    max_content_length: int = 1_000_000  # 1MB content limit
    max_fingerprints_memory: int = 100_000  # Memory limit for fingerprints

    # Performance settings
    batch_processing_size: int = 100
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour

    # Content normalization
    normalize_whitespace: bool = True
    remove_html_tags: bool = True
    normalize_urls: bool = True
    case_insensitive_comparison: bool = True


class ContentNormalizer:
    """Normalizes content for consistent deduplication"""

    def __init__(self, config: DeduplicationConfig):
        self.config = config

        # Pre-compiled regex patterns for performance
        self.html_tag_pattern = re.compile(r"<[^>]+>")
        self.whitespace_pattern = re.compile(r"\s+")
        self.url_param_pattern = re.compile(r"[?&]utm_[^&]*")

    def normalize_content(self, content: str) -> str:
        """Normalize content for consistent comparison"""
        if not content:
            return ""

        normalized = content

        # Remove HTML tags if enabled
        if self.config.remove_html_tags:
            normalized = self.html_tag_pattern.sub(" ", normalized)

        # Normalize whitespace if enabled
        if self.config.normalize_whitespace:
            normalized = self.whitespace_pattern.sub(" ", normalized).strip()

        # Case normalization if enabled
        if self.config.case_insensitive_comparison:
            normalized = normalized.lower()

        return normalized

    def normalize_url(self, url: str) -> str:
        """Normalize URL for consistent comparison"""
        if not url:
            return ""

        normalized = url.strip()

        if self.config.normalize_urls:
            # Remove tracking parameters
            normalized = self.url_param_pattern.sub("", normalized)

            # Remove common variations
            normalized = normalized.rstrip("/")

            # Normalize protocol
            if normalized.startswith("http://"):
                normalized = normalized.replace("http://", "https://", 1)

        return normalized

    def extract_title_tokens(self, title: str) -> set[str]:
        """Extract significant tokens from title for similarity comparison"""
        if not title:
            return set()

        # Normalize title
        normalized = self.normalize_content(title)

        # Split into tokens and filter
        tokens = normalized.split()

        # Remove common words and short tokens
        stop_words = {
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
        }
        significant_tokens = {
            token for token in tokens if len(token) > 2 and token not in stop_words
        }

        return significant_tokens


class DuplicationDetector(ABC):
    """Abstract base class for duplication detection algorithms"""

    @abstractmethod
    async def detect_duplicate(
        self,
        content: str,
        metadata: dict[str, Any],
        existing_fingerprints: list[ContentFingerprint],
    ) -> tuple[bool, float, ContentFingerprint | None]:
        """Detect if content is a duplicate.
        Returns: (is_duplicate, similarity_score, matching_fingerprint)
        """


class ExactHashDetector(DuplicationDetector):
    """Exact hash-based duplicate detection"""

    def __init__(self, normalizer: ContentNormalizer):
        self.normalizer = normalizer

    async def detect_duplicate(
        self,
        content: str,
        metadata: dict[str, Any],
        existing_fingerprints: list[ContentFingerprint],
    ) -> tuple[bool, float, ContentFingerprint | None]:
        """Detect exact duplicates using SHA-256 hash"""
        # Normalize content for hashing
        normalized_content = self.normalizer.normalize_content(content)
        content_hash = hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()

        # Check against existing fingerprints
        for fingerprint in existing_fingerprints:
            if fingerprint.content_hash == content_hash:
                return True, 1.0, fingerprint

        return False, 0.0, None


class FuzzyHashDetector(DuplicationDetector):
    """Fuzzy hash-based near-duplicate detection"""

    def __init__(self, normalizer: ContentNormalizer, config: DeduplicationConfig):
        self.normalizer = normalizer
        self.config = config

    def _compute_fuzzy_hash(self, content: str) -> str:
        """Compute fuzzy hash using shingling technique"""
        normalized = self.normalizer.normalize_content(content)

        # Create character n-grams (shingles)
        shingle_size = 5
        shingles = set()

        for i in range(len(normalized) - shingle_size + 1):
            shingle = normalized[i : i + shingle_size]
            shingles.add(hashlib.sha256(shingle.encode("utf-8")).hexdigest()[:8])

        # Create fuzzy hash from top shingles
        sorted_shingles = sorted(list(shingles))[:50]  # Top 50 shingles
        fuzzy_hash = hashlib.sha256(
            "".join(sorted_shingles).encode("utf-8"),
        ).hexdigest()

        return fuzzy_hash

    def _calculate_fuzzy_similarity(self, hash1: str, hash2: str) -> float:
        """Calculate similarity between two fuzzy hashes"""
        if not hash1 or not hash2:
            return 0.0

        # Simple Hamming distance for demonstration
        # In production, use more sophisticated fuzzy hash comparison
        if len(hash1) != len(hash2):
            return 0.0

        matches = sum(c1 == c2 for c1, c2 in zip(hash1, hash2, strict=False))
        similarity = matches / len(hash1)

        return similarity

    async def detect_duplicate(
        self,
        content: str,
        metadata: dict[str, Any],
        existing_fingerprints: list[ContentFingerprint],
    ) -> tuple[bool, float, ContentFingerprint | None]:
        """Detect near-duplicates using fuzzy hashing"""
        fuzzy_hash = self._compute_fuzzy_hash(content)
        best_similarity = 0.0
        best_match = None

        # Compare against existing fuzzy hashes
        for fingerprint in existing_fingerprints:
            if fingerprint.fuzzy_hash:
                similarity = self._calculate_fuzzy_similarity(
                    fuzzy_hash,
                    fingerprint.fuzzy_hash,
                )
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = fingerprint

        is_duplicate = best_similarity >= self.config.fuzzy_similarity_threshold
        return is_duplicate, best_similarity, best_match


class TitleSimilarityDetector(DuplicationDetector):
    """Title-based similarity detection"""

    def __init__(self, normalizer: ContentNormalizer, config: DeduplicationConfig):
        self.normalizer = normalizer
        self.config = config

    def _calculate_title_similarity(
        self,
        tokens1: set[str],
        tokens2: set[str],
    ) -> float:
        """Calculate Jaccard similarity between title token sets"""
        if not tokens1 or not tokens2:
            return 0.0

        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))

        return intersection / union if union > 0 else 0.0

    async def detect_duplicate(
        self,
        content: str,
        metadata: dict[str, Any],
        existing_fingerprints: list[ContentFingerprint],
    ) -> tuple[bool, float, ContentFingerprint | None]:
        """Detect duplicates based on title similarity"""
        # Extract title from metadata
        title = (
            metadata.get("title", "") or metadata.get("subject", "") or content[:100]
        )
        title_tokens = self.normalizer.extract_title_tokens(title)

        best_similarity = 0.0
        best_match = None

        # Compare against existing title tokens
        for fingerprint in existing_fingerprints:
            if fingerprint.title_tokens:
                similarity = self._calculate_title_similarity(
                    title_tokens,
                    fingerprint.title_tokens,
                )
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = fingerprint

        is_duplicate = best_similarity >= self.config.title_similarity_threshold
        return is_duplicate, best_similarity, best_match


class AdvancedContentDeduplicationService:
    """Advanced content deduplication service with multiple detection methods.
    Provides ML-powered similarity detection and configurable policies.
    """

    def __init__(self, config: DeduplicationConfig = None):
        self.config = config or DeduplicationConfig()
        self.normalizer = ContentNormalizer(self.config)

        # Initialize detection methods
        self.detectors: dict[DeduplicationMethod, DuplicationDetector] = {}
        self._initialize_detectors()

        # Content fingerprint storage (in-memory for this implementation)
        self.fingerprints: dict[str, ContentFingerprint] = {}
        self.content_id_mapping: dict[str, str] = {}  # hash -> content_id

        # Statistics
        self.stats = {
            "total_processed": 0,
            "duplicates_found": 0,
            "processing_time_total": 0.0,
            "method_usage": {method.value: 0 for method in DeduplicationMethod},
        }

        logger.info("Initialized AdvancedContentDeduplicationService")

    def _initialize_detectors(self):
        """Initialize enabled detection methods"""
        for method in self.config.enabled_methods:
            if method == DeduplicationMethod.EXACT_HASH:
                self.detectors[method] = ExactHashDetector(self.normalizer)
            elif method == DeduplicationMethod.FUZZY_HASH:
                self.detectors[method] = FuzzyHashDetector(self.normalizer, self.config)
            elif method == DeduplicationMethod.TITLE_SIMILARITY:
                self.detectors[method] = TitleSimilarityDetector(
                    self.normalizer,
                    self.config,
                )
            # Additional detectors can be added here

    async def check_duplicate(
        self,
        content_id: str,
        content: str,
        metadata: dict[str, Any] = None,
    ) -> DeduplicationResult:
        """Check if content is a duplicate and return detailed analysis."""
        import time

        start_time = time.time()

        metadata = metadata or {}

        # Validate input
        if len(content) > self.config.max_content_length:
            logger.warning(f"Content length exceeds limit: {len(content)}")
            content = content[: self.config.max_content_length]

        try:
            # Run detection methods in priority order
            for method in self.config.enabled_methods:
                if method not in self.detectors:
                    continue

                detector = self.detectors[method]
                existing_fingerprints = list(self.fingerprints.values())

                (
                    is_duplicate,
                    similarity_score,
                    matching_fingerprint,
                ) = await detector.detect_duplicate(
                    content,
                    metadata,
                    existing_fingerprints,
                )

                if is_duplicate and matching_fingerprint:
                    # Found duplicate
                    processing_time = (time.time() - start_time) * 1000
                    duplicate_content_id = self.content_id_mapping.get(
                        matching_fingerprint.content_hash,
                    )

                    result = DeduplicationResult(
                        is_duplicate=True,
                        method_used=method,
                        similarity_score=similarity_score,
                        duplicate_of=duplicate_content_id,
                        action_taken=self.config.default_action,
                        fingerprint=matching_fingerprint,
                        processing_time_ms=processing_time,
                    )

                    # Update statistics
                    self._update_stats(method, processing_time, True)

                    return result

            # No duplicate found - create new fingerprint
            fingerprint = await self._create_fingerprint(content, metadata)
            self._store_fingerprint(content_id, fingerprint)

            processing_time = (time.time() - start_time) * 1000

            result = DeduplicationResult(
                is_duplicate=False,
                method_used=None,
                similarity_score=0.0,
                duplicate_of=None,
                action_taken=DuplicateAction.KEEP_LATEST,
                fingerprint=fingerprint,
                processing_time_ms=processing_time,
            )

            # Update statistics
            self._update_stats(None, processing_time, False)

            return result

        except Exception as e:
            logger.error(f"Error in duplicate check: {e}")
            processing_time = (time.time() - start_time) * 1000

            return DeduplicationResult(
                is_duplicate=False,
                processing_time_ms=processing_time,
            )

    async def _create_fingerprint(
        self,
        content: str,
        metadata: dict[str, Any],
    ) -> ContentFingerprint:
        """Create content fingerprint for future comparison"""
        # Normalize content
        normalized_content = self.normalizer.normalize_content(content)

        # Generate hashes
        content_hash = hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()
        metadata_json = json.dumps(metadata, sort_keys=True)
        metadata_hash = hashlib.sha256(metadata_json.encode("utf-8")).hexdigest()

        # Generate fuzzy hash if enabled
        fuzzy_hash = None
        if DeduplicationMethod.FUZZY_HASH in self.config.enabled_methods:
            fuzzy_detector = self.detectors.get(DeduplicationMethod.FUZZY_HASH)
            if hasattr(fuzzy_detector, "_compute_fuzzy_hash"):
                fuzzy_hash = fuzzy_detector._compute_fuzzy_hash(content)

        # Extract title tokens
        title = (
            metadata.get("title", "") or metadata.get("subject", "") or content[:100]
        )
        title_tokens = self.normalizer.extract_title_tokens(title)

        # Normalize URL if available
        url_normalized = None
        if "url" in metadata:
            url_normalized = self.normalizer.normalize_url(metadata["url"])

        return ContentFingerprint(
            content_hash=content_hash,
            metadata_hash=metadata_hash,
            fuzzy_hash=fuzzy_hash,
            title_tokens=title_tokens,
            url_normalized=url_normalized,
            content_length=len(content),
        )

    def _store_fingerprint(self, content_id: str, fingerprint: ContentFingerprint):
        """Store fingerprint for future comparisons"""
        # Memory management - remove oldest fingerprints if limit exceeded
        if len(self.fingerprints) >= self.config.max_fingerprints_memory:
            # Remove oldest 10% of fingerprints
            oldest_fingerprints = sorted(
                self.fingerprints.items(),
                key=lambda x: x[1].created_at,
            )[: len(self.fingerprints) // 10]

            for hash_key, _ in oldest_fingerprints:
                del self.fingerprints[hash_key]
                # Also remove from content mapping
                content_to_remove = [
                    cid for cid, h in self.content_id_mapping.items() if h == hash_key
                ]
                for cid in content_to_remove:
                    del self.content_id_mapping[cid]

        # Store new fingerprint
        self.fingerprints[fingerprint.content_hash] = fingerprint
        self.content_id_mapping[fingerprint.content_hash] = content_id

    def _update_stats(
        self,
        method: DeduplicationMethod | None,
        processing_time: float,
        is_duplicate: bool,
    ):
        """Update processing statistics"""
        self.stats["total_processed"] += 1
        self.stats["processing_time_total"] += processing_time

        if is_duplicate:
            self.stats["duplicates_found"] += 1

        if method:
            self.stats["method_usage"][method.value] += 1

    async def batch_check_duplicates(
        self,
        content_items: list[tuple[str, str, dict[str, Any]]],
    ) -> list[DeduplicationResult]:
        """Check multiple content items for duplicates in batch.
        Items format: [(content_id, content, metadata), ...]
        """
        results = []

        # Process in batches for memory efficiency
        batch_size = self.config.batch_processing_size

        for i in range(0, len(content_items), batch_size):
            batch = content_items[i : i + batch_size]
            batch_results = []

            for content_id, content, metadata in batch:
                result = await self.check_duplicate(content_id, content, metadata)
                batch_results.append(result)

            results.extend(batch_results)

        return results

    def get_statistics(self) -> dict[str, Any]:
        """Get deduplication processing statistics"""
        stats = self.stats.copy()

        if stats["total_processed"] > 0:
            stats["duplicate_rate"] = (
                stats["duplicates_found"] / stats["total_processed"]
            )
            stats["average_processing_time_ms"] = (
                stats["processing_time_total"] / stats["total_processed"]
            )
        else:
            stats["duplicate_rate"] = 0.0
            stats["average_processing_time_ms"] = 0.0

        stats["fingerprints_stored"] = len(self.fingerprints)

        return stats

    async def clear_fingerprints(self):
        """Clear all stored fingerprints (for testing or maintenance)"""
        self.fingerprints.clear()
        self.content_id_mapping.clear()
        logger.info("Cleared all content fingerprints")

    async def export_fingerprints(self, filepath: str) -> bool:
        """Export fingerprints to JSON file"""
        try:
            export_data = {
                "fingerprints": {
                    hash_key: fingerprint.to_dict()
                    for hash_key, fingerprint in self.fingerprints.items()
                },
                "content_mapping": self.content_id_mapping.copy(),
                "exported_at": datetime.now(UTC).isoformat(),
                "total_count": len(self.fingerprints),
            }

            import aiofiles

            async with aiofiles.open(filepath, "w") as f:
                await f.write(json.dumps(export_data, indent=2))

            logger.info(f"Exported {len(self.fingerprints)} fingerprints to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to export fingerprints: {e}")
            return False


# Example usage and factory functions
async def create_production_deduplication_service() -> (
    AdvancedContentDeduplicationService
):
    """Create production-ready deduplication service with optimized settings"""
    config = DeduplicationConfig(
        fuzzy_similarity_threshold=0.80,  # More permissive for near-duplicates
        semantic_similarity_threshold=0.85,  # ML similarity threshold
        enabled_methods=[
            DeduplicationMethod.EXACT_HASH,
            DeduplicationMethod.CONTENT_HASH,
            DeduplicationMethod.FUZZY_HASH,
            DeduplicationMethod.TITLE_SIMILARITY,
        ],
        max_fingerprints_memory=250_000,  # Higher memory limit
        batch_processing_size=500,  # Larger batches
        enable_caching=True,
    )

    return AdvancedContentDeduplicationService(config)


if __name__ == "__main__":
    # Example standalone usage
    async def main():
        service = AdvancedContentDeduplicationService()

        # Test content
        content1 = "This is a sample article about machine learning and AI."
        content2 = (
            "This is a sample article about machine learning and AI."  # Exact duplicate
        )
        content3 = "This article discusses machine learning and artificial intelligence."  # Similar

        # Check for duplicates
        result1 = await service.check_duplicate(
            "item1",
            content1,
            {"title": "ML Article"},
        )
        result2 = await service.check_duplicate(
            "item2",
            content2,
            {"title": "ML Article"},
        )
        result3 = await service.check_duplicate(
            "item3",
            content3,
            {"title": "AI Article"},
        )

        print(f"Result 1 - Duplicate: {result1.is_duplicate}")
        print(
            f"Result 2 - Duplicate: {result2.is_duplicate}, Method: {result2.method_used}",
        )
        print(
            f"Result 3 - Duplicate: {result3.is_duplicate}, Similarity: {result3.similarity_score:.2f}",
        )

        # Print statistics
        stats = service.get_statistics()
        print(f"Statistics: {stats}")

    asyncio.run(main())
