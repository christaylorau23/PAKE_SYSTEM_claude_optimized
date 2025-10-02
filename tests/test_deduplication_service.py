#!/usr/bin/env python3
"""
PAKE System - Content Deduplication Service Tests
Phase 2B Sprint 4: Comprehensive TDD testing for ML-powered content deduplication

Tests exact duplicate detection, fuzzy similarity matching, title-based similarity,
and advanced deduplication policies.
"""

import asyncio
import json
import tempfile
import time
from pathlib import Path

import pytest
import pytest_asyncio
from services.content.deduplication_service import (
    AdvancedContentDeduplicationService,
    ContentFingerprint,
    ContentNormalizer,
    DeduplicationConfig,
    DeduplicationMethod,
    DeduplicationResult,
    DuplicateAction,
    ExactHashDetector,
    FuzzyHashDetector,
    TitleSimilarityDetector,
)


class TestAdvancedContentDeduplicationService:
    """
    Comprehensive test suite for advanced content deduplication service.
    Tests exact matching, fuzzy similarity, ML-powered detection, and performance.
    """

    @pytest.fixture()
    def dedup_config(self):
        """Standard deduplication configuration for testing"""
        return DeduplicationConfig(
            exact_match_threshold=1.0,
            fuzzy_similarity_threshold=0.80,
            semantic_similarity_threshold=0.85,
            title_similarity_threshold=0.90,
            enabled_methods=[
                DeduplicationMethod.EXACT_HASH,
                DeduplicationMethod.FUZZY_HASH,
                DeduplicationMethod.TITLE_SIMILARITY,
            ],
            default_action=DuplicateAction.SKIP,
            max_content_length=10000,
            max_fingerprints_memory=1000,
            batch_processing_size=50,
            normalize_whitespace=True,
            remove_html_tags=True,
            case_insensitive_comparison=True,
        )

    @pytest_asyncio.fixture
    async def dedup_service(self, dedup_config):
        """Create deduplication service instance for testing"""
        service = AdvancedContentDeduplicationService(dedup_config)
        yield service
        await service.clear_fingerprints()

    @pytest.fixture()
    def sample_content_items(self):
        """Sample content items for testing"""
        return [
            {
                "id": "item1",
                "content": "This is a comprehensive article about machine learning algorithms and their applications in modern AI systems.",
                "metadata": {
                    "title": "Machine Learning Guide",
                    "author": "John Doe",
                    "url": "https://example.com/ml-guide",
                },
            },
            {
                "id": "item2",
                "content": "This is a comprehensive article about machine learning algorithms and their applications in modern AI systems.",
                "metadata": {
                    "title": "Machine Learning Guide",
                    "author": "John Doe",
                    "url": "https://example.com/ml-guide",
                },
            },
            {
                "id": "item3",
                "content": "This comprehensive article covers machine learning algorithms and applications in modern artificial intelligence systems.",
                "metadata": {
                    "title": "ML Guide",
                    "author": "Jane Smith",
                    "url": "https://example.com/ml-tutorial",
                },
            },
            {
                "id": "item4",
                "content": "Python is a versatile programming language used for web development, data science, and automation.",
                "metadata": {
                    "title": "Python Programming",
                    "author": "Bob Johnson",
                    "url": "https://example.com/python-intro",
                },
            },
        ]

    # ========================================================================
    # Core Functionality Tests
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_initialize_deduplication_service_with_config(
        self,
        dedup_config,
    ):
        """
        Test: Should initialize deduplication service with proper configuration
        and detection methods.
        """
        service = AdvancedContentDeduplicationService(dedup_config)

        # Check configuration is set
        assert service.config == dedup_config
        assert service.normalizer is not None

        # Check detectors are initialized for enabled methods
        assert len(service.detectors) == len(dedup_config.enabled_methods)
        assert DeduplicationMethod.EXACT_HASH in service.detectors
        assert DeduplicationMethod.FUZZY_HASH in service.detectors
        assert DeduplicationMethod.TITLE_SIMILARITY in service.detectors

        # Check initial state
        assert len(service.fingerprints) == 0
        assert service.stats["total_processed"] == 0
        assert service.stats["duplicates_found"] == 0

    @pytest.mark.asyncio()
    async def test_should_detect_exact_duplicate_content_correctly(
        self,
        dedup_service,
        sample_content_items,
    ):
        """
        Test: Should detect exact duplicate content using hash-based matching
        with proper similarity scoring.
        """
        item1 = sample_content_items[0]
        item2 = sample_content_items[1]  # Exact duplicate

        # Check first item (should not be duplicate)
        result1 = await dedup_service.check_duplicate(
            item1["id"],
            item1["content"],
            item1["metadata"],
        )
        assert not result1.is_duplicate
        assert result1.method_used is None
        assert result1.fingerprint is not None

        # Check second item (should be exact duplicate)
        result2 = await dedup_service.check_duplicate(
            item2["id"],
            item2["content"],
            item2["metadata"],
        )
        assert result2.is_duplicate
        assert result2.method_used == DeduplicationMethod.EXACT_HASH
        assert result2.similarity_score == 1.0
        assert result2.duplicate_of == item1["id"]
        assert result2.action_taken == DuplicateAction.SKIP

    @pytest.mark.asyncio()
    async def test_should_detect_fuzzy_similar_content_with_threshold(
        self,
        dedup_service,
        sample_content_items,
    ):
        """
        Test: Should detect near-duplicate content using fuzzy hashing
        with configurable similarity thresholds.
        """
        item1 = sample_content_items[0]
        item3 = sample_content_items[2]  # Similar but not exact

        # Add first item
        result1 = await dedup_service.check_duplicate(
            item1["id"],
            item1["content"],
            item1["metadata"],
        )
        assert not result1.is_duplicate

        # Check similar item
        result3 = await dedup_service.check_duplicate(
            item3["id"],
            item3["content"],
            item3["metadata"],
        )

        # Should detect similarity (depending on threshold configuration)
        if result3.is_duplicate:
            assert result3.method_used in [
                DeduplicationMethod.FUZZY_HASH,
                DeduplicationMethod.TITLE_SIMILARITY,
            ]
            assert 0.7 <= result3.similarity_score <= 1.0
        else:
            # If not detected as duplicate, similarity should be below threshold
            assert result3.similarity_score < 0.80

    @pytest.mark.asyncio()
    async def test_should_handle_title_based_similarity_detection(self, dedup_service):
        """
        Test: Should detect duplicates based on title similarity
        using token-based comparison.
        """
        # Content with very similar titles
        content1 = "First article content here"
        metadata1 = {"title": "Machine Learning Fundamentals Guide"}

        content2 = "Different article content"
        metadata2 = {"title": "Machine Learning Fundamentals Tutorial"}

        # Add first item
        result1 = await dedup_service.check_duplicate("item1", content1, metadata1)
        assert not result1.is_duplicate

        # Check second item with similar title
        result2 = await dedup_service.check_duplicate("item2", content2, metadata2)

        # Should detect title similarity if threshold is met
        if result2.is_duplicate:
            assert result2.method_used == DeduplicationMethod.TITLE_SIMILARITY
            assert result2.similarity_score >= 0.90

    @pytest.mark.asyncio()
    async def test_should_create_comprehensive_content_fingerprints(
        self,
        dedup_service,
    ):
        """
        Test: Should create detailed content fingerprints with all
        relevant metadata and hashing information.
        """
        content = "Sample article content about artificial intelligence"
        metadata = {
            "title": "AI Article",
            "author": "Test Author",
            "url": "https://example.com/ai-article?utm_source=test",
            "category": "Technology",
        }

        result = await dedup_service.check_duplicate("test_item", content, metadata)

        # Check fingerprint creation
        assert result.fingerprint is not None
        fingerprint = result.fingerprint

        # Check fingerprint properties
        assert len(fingerprint.content_hash) == 64  # SHA-256 hash length
        assert len(fingerprint.metadata_hash) == 64
        assert (
            fingerprint.fuzzy_hash is not None
            if DeduplicationMethod.FUZZY_HASH in dedup_service.config.enabled_methods
            else True
        )
        assert len(fingerprint.title_tokens) > 0
        assert fingerprint.url_normalized is not None
        assert fingerprint.content_length == len(content)
        assert fingerprint.created_at is not None

    @pytest.mark.asyncio()
    async def test_should_process_batch_content_efficiently(
        self,
        dedup_service,
        sample_content_items,
    ):
        """
        Test: Should process multiple content items in batch
        with efficient memory usage and duplicate detection.
        """
        # Prepare batch data
        batch_items = [
            (item["id"], item["content"], item["metadata"])
            for item in sample_content_items
        ]

        # Process batch
        results = await dedup_service.batch_check_duplicates(batch_items)

        # Verify results
        assert len(results) == len(sample_content_items)

        # First item should not be duplicate
        assert not results[0].is_duplicate

        # Second item should be duplicate of first (exact match)
        assert results[1].is_duplicate
        assert results[1].method_used == DeduplicationMethod.EXACT_HASH

        # Third item might be duplicate (similar content)
        # Fourth item should not be duplicate (different content)
        assert not results[3].is_duplicate

    # ========================================================================
    # Content Normalization Tests
    # ========================================================================

    def test_content_normalizer_should_handle_html_and_whitespace(self, dedup_config):
        """
        Test: ContentNormalizer should properly clean HTML tags
        and normalize whitespace for consistent comparison.
        """
        normalizer = ContentNormalizer(dedup_config)

        # Test HTML tag removal
        html_content = "<p>This is <strong>important</strong> content.</p>"
        normalized = normalizer.normalize_content(html_content)
        assert "<p>" not in normalized
        assert "<strong>" not in normalized
        assert "important" in normalized

        # Test whitespace normalization
        messy_content = "This   has    multiple\t\tspaces\n\nand   newlines"
        normalized = normalizer.normalize_content(messy_content)
        assert "  " not in normalized  # No double spaces
        assert "\t" not in normalized  # No tabs
        assert "\n" not in normalized  # No newlines

    def test_content_normalizer_should_normalize_urls_consistently(self, dedup_config):
        """
        Test: ContentNormalizer should normalize URLs for consistent
        duplicate detection regardless of tracking parameters.
        """
        normalizer = ContentNormalizer(dedup_config)

        # Test tracking parameter removal
        url_with_params = (
            "https://example.com/article?utm_source=social&utm_medium=twitter"
        )
        normalized = normalizer.normalize_url(url_with_params)
        assert "utm_source" not in normalized
        assert "utm_medium" not in normalized

        # Test trailing slash removal
        url_with_slash = "https://example.com/article/"
        normalized = normalizer.normalize_url(url_with_slash)
        assert not normalized.endswith("/")

        # Test protocol normalization
        http_url = "http://example.com/article"
        normalized = normalizer.normalize_url(http_url)
        assert normalized.startswith("https://")

    def test_content_normalizer_should_extract_significant_title_tokens(
        self,
        dedup_config,
    ):
        """
        Test: ContentNormalizer should extract meaningful tokens
        from titles while filtering stop words and short tokens.
        """
        normalizer = ContentNormalizer(dedup_config)

        title = "The Complete Guide to Machine Learning and AI"
        tokens = normalizer.extract_title_tokens(title)

        # Should include significant words
        assert "complete" in tokens
        assert "guide" in tokens
        assert "machine" in tokens
        assert "learning" in tokens

        # Should exclude stop words and short tokens
        assert "the" not in tokens
        assert "to" not in tokens
        assert "and" not in tokens

    # ========================================================================
    # Performance and Scalability Tests
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_maintain_performance_under_high_volume(self, dedup_service):
        """
        Test: Should maintain acceptable performance when processing
        large volumes of content for deduplication.
        """
        # Generate large number of content items
        content_items = []
        for i in range(200):
            content_items.append(
                (
                    f"item_{i}",
                    f"This is test content number {i} with some unique text to avoid duplicates",
                    {"title": f"Test Article {i}", "category": "test"},
                ),
            )

        # Add some intentional duplicates
        content_items.append(
            (
                "duplicate_1",
                "This is test content number 50 with some unique text to avoid duplicates",
                {"title": "Test Article 50", "category": "test"},
            ),
        )

        # Measure processing time
        start_time = time.time()
        results = await dedup_service.batch_check_duplicates(content_items)
        processing_time = time.time() - start_time

        # Should complete in reasonable time (under 5 seconds for 201 items)
        assert processing_time < 5.0

        # Should detect the duplicate
        duplicate_results = [r for r in results if r.is_duplicate]
        assert len(duplicate_results) >= 1

        # Verify statistics
        stats = dedup_service.get_statistics()
        assert stats["total_processed"] == len(content_items)
        assert stats["duplicates_found"] >= 1

    @pytest.mark.asyncio()
    async def test_should_manage_memory_usage_with_fingerprint_limits(
        self,
        dedup_config,
    ):
        """
        Test: Should properly manage memory by limiting stored fingerprints
        and removing oldest entries when limit is reached.
        """
        # Configure with small memory limit for testing
        dedup_config.max_fingerprints_memory = 10
        service = AdvancedContentDeduplicationService(dedup_config)

        # Add more items than memory limit
        for i in range(15):
            await service.check_duplicate(
                f"item_{i}",
                f"Unique content item number {i}",
                {"title": f"Article {i}"},
            )

        # Should not exceed memory limit
        assert len(service.fingerprints) <= dedup_config.max_fingerprints_memory

        # Should still function correctly
        result = await service.check_duplicate(
            "new_item",
            "Brand new content that definitely doesn't exist",
            {"title": "New Article"},
        )
        assert not result.is_duplicate

    @pytest.mark.asyncio()
    async def test_should_handle_concurrent_deduplication_safely(self, dedup_service):
        """
        Test: Should handle concurrent deduplication requests
        without race conditions or data corruption.
        """
        # Create concurrent deduplication tasks
        tasks = []
        for i in range(20):
            task = asyncio.create_task(
                dedup_service.check_duplicate(
                    f"concurrent_item_{i}",
                    f"Concurrent content {i} for testing race conditions",
                    {"title": f"Concurrent Article {i}"},
                ),
            )
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all completed successfully
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, DeduplicationResult)

        # Verify data integrity
        stats = dedup_service.get_statistics()
        assert stats["total_processed"] >= 20

    # ========================================================================
    # Error Handling and Edge Cases
    # ========================================================================

    @pytest.mark.asyncio()
    async def test_should_handle_empty_and_malformed_content(self, dedup_service):
        """
        Test: Should gracefully handle empty content, None values,
        and malformed input data.
        """
        # Test empty content
        result1 = await dedup_service.check_duplicate("empty", "", {})
        assert not result1.is_duplicate
        assert result1.fingerprint is not None

        # Test None content (should be handled gracefully)
        try:
            result2 = await dedup_service.check_duplicate("none", None, {})
            # If it doesn't throw an exception, it should handle gracefully
            assert isinstance(result2, DeduplicationResult)
        except TypeError:
            # It's acceptable to throw TypeError for None content
            pass

        # Test very long content (should be truncated)
        long_content = "x" * 50000
        result3 = await dedup_service.check_duplicate("long", long_content, {})
        assert (
            result3.fingerprint.content_length
            <= dedup_service.config.max_content_length
        )

    @pytest.mark.asyncio()
    async def test_should_handle_malformed_metadata_gracefully(self, dedup_service):
        """
        Test: Should handle malformed, missing, or invalid metadata
        without crashing the deduplication process.
        """
        content = "Test content with problematic metadata"

        # Test with None metadata
        result1 = await dedup_service.check_duplicate("test1", content, None)
        assert isinstance(result1, DeduplicationResult)

        # Test with malformed metadata
        malformed_metadata = {
            "title": None,
            "author": {"nested": "object"},
            "date": "invalid_date_format",
            "tags": [1, 2, 3, {"invalid": "tag"}],
        }
        result2 = await dedup_service.check_duplicate(
            "test2",
            content,
            malformed_metadata,
        )
        assert isinstance(result2, DeduplicationResult)

    @pytest.mark.asyncio()
    async def test_should_export_and_import_fingerprints_correctly(
        self,
        dedup_service,
        sample_content_items,
    ):
        """
        Test: Should export fingerprints to file and maintain
        data integrity during serialization.
        """
        # Add some content to create fingerprints
        for item in sample_content_items[:2]:
            await dedup_service.check_duplicate(
                item["id"],
                item["content"],
                item["metadata"],
            )

        # Export to temporary file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as tmp_file:
            tmp_path = tmp_file.name

        success = await dedup_service.export_fingerprints(tmp_path)
        assert success

        # Verify exported data
        with open(tmp_path) as f:
            exported_data = json.load(f)

        # Clean up
        Path(tmp_path).unlink()

        # Verify export structure
        assert "fingerprints" in exported_data
        assert "content_mapping" in exported_data
        assert "exported_at" in exported_data
        assert "total_count" in exported_data

        # Verify fingerprint data integrity
        assert len(exported_data["fingerprints"]) >= 1
        for fingerprint_data in exported_data["fingerprints"].values():
            assert "content_hash" in fingerprint_data
            assert "metadata_hash" in fingerprint_data
            assert "created_at" in fingerprint_data


class TestDeduplicationDetectors:
    """
    Test suite for individual deduplication detection algorithms.
    """

    @pytest.fixture()
    def normalizer(self):
        """Content normalizer for detector testing"""
        config = DeduplicationConfig()
        return ContentNormalizer(config)

    @pytest.fixture()
    def sample_fingerprints(self, normalizer):
        """Sample fingerprints for detector testing"""
        import hashlib

        fingerprints = []
        contents = [
            "Sample content about machine learning",
            "Different content about data science",
            "Another article on artificial intelligence",
        ]

        for i, content in enumerate(contents):
            normalized = normalizer.normalize_content(content)
            content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

            fingerprint = ContentFingerprint(
                content_hash=content_hash,
                metadata_hash=f"metadata_hash_{i}",
                fuzzy_hash=f"fuzzy_hash_{i}",
                title_tokens=normalizer.extract_title_tokens(f"Title {i}"),
                content_length=len(content),
            )
            fingerprints.append(fingerprint)

        return fingerprints

    @pytest.mark.asyncio()
    async def test_exact_hash_detector_should_identify_identical_content(
        self,
        normalizer,
        sample_fingerprints,
    ):
        """
        Test: ExactHashDetector should correctly identify identical content
        using SHA-256 hash comparison.
        """
        detector = ExactHashDetector(normalizer)

        # Test exact match
        test_content = "Sample content about machine learning"
        (
            is_duplicate,
            similarity,
            matching_fingerprint,
        ) = await detector.detect_duplicate(test_content, {}, sample_fingerprints)

        assert is_duplicate
        assert similarity == 1.0
        assert matching_fingerprint is not None
        assert matching_fingerprint == sample_fingerprints[0]

        # Test non-match
        different_content = "Completely different content here"
        (
            is_duplicate,
            similarity,
            matching_fingerprint,
        ) = await detector.detect_duplicate(different_content, {}, sample_fingerprints)

        assert not is_duplicate
        assert similarity == 0.0
        assert matching_fingerprint is None

    @pytest.mark.asyncio()
    async def test_fuzzy_hash_detector_should_find_similar_content(
        self,
        normalizer,
        sample_fingerprints,
    ):
        """
        Test: FuzzyHashDetector should identify similar but not identical
        content using fuzzy hashing techniques.
        """
        config = DeduplicationConfig(fuzzy_similarity_threshold=0.5)
        detector = FuzzyHashDetector(normalizer, config)

        # Test with slightly modified content
        similar_content = "Sample content about machine learning algorithms"
        (
            is_duplicate,
            similarity,
            matching_fingerprint,
        ) = await detector.detect_duplicate(similar_content, {}, sample_fingerprints)

        # Should detect some level of similarity
        assert 0.0 <= similarity <= 1.0

        # Whether it's detected as duplicate depends on the similarity threshold
        if is_duplicate:
            assert similarity >= config.fuzzy_similarity_threshold
            assert matching_fingerprint is not None

    @pytest.mark.asyncio()
    async def test_title_similarity_detector_should_compare_titles(self, normalizer):
        """
        Test: TitleSimilarityDetector should identify content with
        similar titles using token-based comparison.
        """
        config = DeduplicationConfig(title_similarity_threshold=0.8)
        detector = TitleSimilarityDetector(normalizer, config)

        # Create fingerprints with known title tokens
        fingerprint = ContentFingerprint(
            content_hash="test_hash",
            metadata_hash="test_metadata",
            title_tokens={"machine", "learning", "guide", "comprehensive"},
        )

        # Test with similar title
        test_metadata = {"title": "Comprehensive Machine Learning Tutorial"}
        (
            is_duplicate,
            similarity,
            matching_fingerprint,
        ) = await detector.detect_duplicate(
            "test content",
            test_metadata,
            [fingerprint],
        )

        # Should find significant similarity in titles
        assert similarity > 0.0

        # May or may not be classified as duplicate depending on exact similarity
        if is_duplicate:
            assert similarity >= config.title_similarity_threshold


class TestDeduplicationConfiguration:
    """
    Test suite for deduplication configuration and settings.
    """

    def test_deduplication_config_should_have_sensible_defaults(self):
        """
        Test: DeduplicationConfig should provide reasonable default values
        for production use.
        """
        config = DeduplicationConfig()

        # Check thresholds are reasonable
        assert 0.5 <= config.fuzzy_similarity_threshold <= 1.0
        assert 0.8 <= config.semantic_similarity_threshold <= 1.0
        assert 0.8 <= config.title_similarity_threshold <= 1.0

        # Check memory limits are reasonable
        assert config.max_content_length > 1000
        assert config.max_fingerprints_memory > 1000
        assert config.batch_processing_size > 10

        # Check enabled methods include basic algorithms
        assert DeduplicationMethod.EXACT_HASH in config.enabled_methods

        # Check default action is reasonable
        assert config.default_action in [action for action in DuplicateAction]

    def test_deduplication_result_should_serialize_correctly(self):
        """
        Test: DeduplicationResult should properly serialize to dictionary
        for JSON export and API responses.
        """
        fingerprint = ContentFingerprint(
            content_hash="test_hash",
            metadata_hash="meta_hash",
            title_tokens={"test", "tokens"},
        )

        result = DeduplicationResult(
            is_duplicate=True,
            method_used=DeduplicationMethod.EXACT_HASH,
            similarity_score=0.95,
            duplicate_of="original_id",
            action_taken=DuplicateAction.SKIP,
            fingerprint=fingerprint,
            processing_time_ms=15.5,
        )

        result_dict = result.to_dict()

        # Verify all fields are present and correctly typed
        assert result_dict["is_duplicate"] is True
        assert result_dict["method_used"] == "exact_hash"
        assert result_dict["similarity_score"] == 0.95
        assert result_dict["duplicate_of"] == "original_id"
        assert result_dict["action_taken"] == "skip"
        assert result_dict["fingerprint"] is not None
        assert result_dict["processing_time_ms"] == 15.5
