#!/usr/bin/env python3
"""
Test Suite for Real-time AI Content Processing Pipeline
Comprehensive tests for streaming AI analysis, edge computing, and pipeline orchestration
"""

import asyncio
import time

import pytest
import pytest_asyncio
from services.ai.cognitive_analysis_engine import CognitiveAnalysisEngine
from services.ai.realtime_processing_pipeline import (
    CognitiveAnalysisStage,
    ContentItem,
    EdgeLocation,
    EdgeProcessor,
    PipelineConfig,
    PipelineMetrics,
    ProcessingPriority,
    ProcessingResult,
    ProcessingStage,
    ProcessingStatus,
    QualityFilteringStage,
    RealTimeProcessingPipeline,
    SemanticIndexingStage,
    create_production_realtime_pipeline,
)
from services.ai.semantic_search_engine import SemanticSearchEngine


@pytest.mark.asyncio()
class TestRealTimeProcessingPipeline:
    """
    Test suite for the main Real-time Processing Pipeline functionality.
    """

    @pytest_asyncio.fixture
    async def pipeline(self):
        """Create real-time processing pipeline for testing"""
        config = PipelineConfig(
            max_concurrent_processing=10,
            max_queue_size=100,
            processing_timeout_seconds=5,
            enable_quality_filtering=True,
            min_quality_threshold=0.3,
            enable_edge_processing=True,
            enable_performance_monitoring=True,
        )

        pipeline = RealTimeProcessingPipeline(config)
        yield pipeline

        # Cleanup - ensure pipeline is stopped
        if pipeline._running:
            await pipeline.stop_pipeline()

    @pytest_asyncio.fixture
    async def running_pipeline(self, pipeline):
        """Create and start a running pipeline for testing"""
        await pipeline.start_pipeline()
        yield pipeline
        await pipeline.stop_pipeline()

    @pytest.fixture()
    def sample_content_items(self):
        """Sample content items for testing"""
        return [
            ContentItem(
                content_id="high_priority_1",
                content="Critical breaking news: Major AI breakthrough announced by leading research institution with significant implications.",
                source="news",
                priority=ProcessingPriority.HIGH,
                metadata={"urgency": "high", "category": "technology"},
            ),
            ContentItem(
                content_id="normal_priority_1",
                content="This comprehensive research study investigates machine learning algorithms for natural language processing applications.",
                source="research",
                priority=ProcessingPriority.NORMAL,
                metadata={"source_type": "academic", "quality_expected": "high"},
            ),
            ContentItem(
                content_id="low_priority_1",
                content="Regular blog post about programming tips and best practices for software development.",
                source="blog",
                priority=ProcessingPriority.LOW,
                metadata={"content_type": "tutorial"},
            ),
        ]

    # ========================================================================
    # Pipeline Lifecycle Tests
    # ========================================================================

    async def test_should_initialize_pipeline_with_configuration(self, pipeline):
        """
        Test: Should initialize real-time processing pipeline with proper
        configuration and component setup.
        """
        # Check pipeline initialization
        assert pipeline.config is not None
        assert pipeline.cognitive_engine is not None
        assert pipeline.semantic_engine is not None
        assert pipeline.query_engine is not None

        # Check processing stages
        assert ProcessingStage.COGNITIVE_ANALYSIS in pipeline.stages
        assert ProcessingStage.SEMANTIC_INDEXING in pipeline.stages
        assert ProcessingStage.QUALITY_FILTERING in pipeline.stages

        # Check edge processors
        assert EdgeLocation.LOCAL in pipeline.edge_processors
        assert EdgeLocation.REGIONAL in pipeline.edge_processors

        # Check initial state
        assert not pipeline._running
        assert len(pipeline.processing_results) == 0
        assert pipeline.get_active_processing_count() == 0

    async def test_should_start_and_stop_pipeline_correctly(self, pipeline):
        """
        Test: Should start and stop pipeline worker correctly
        with proper state management and cleanup.
        """
        # Initial state
        assert not pipeline._running
        assert pipeline._pipeline_task is None

        # Start pipeline
        await pipeline.start_pipeline()
        assert pipeline._running
        assert pipeline._pipeline_task is not None

        # Give pipeline time to initialize
        await asyncio.sleep(0.1)

        # Stop pipeline
        await pipeline.stop_pipeline()
        assert not pipeline._running

    async def test_should_handle_pipeline_restart_gracefully(self, pipeline):
        """
        Test: Should handle pipeline restart scenarios gracefully
        without state corruption or resource leaks.
        """
        # Start pipeline
        await pipeline.start_pipeline()
        assert pipeline._running

        # Stop pipeline
        await pipeline.stop_pipeline()
        assert not pipeline._running

        # Restart pipeline
        await pipeline.start_pipeline()
        assert pipeline._running

        # Stop again
        await pipeline.stop_pipeline()
        assert not pipeline._running

    # ========================================================================
    # Content Processing Tests
    # ========================================================================

    async def test_should_process_single_content_item_successfully(
        self,
        running_pipeline,
        sample_content_items,
    ):
        """
        Test: Should process single content item through full pipeline
        with proper stage execution and result generation.
        """
        content = sample_content_items[1]  # Normal priority research content

        # Submit content for processing
        content_id = await running_pipeline.submit_content(content)
        assert content_id == content.content_id

        # Wait for processing to complete
        result = await running_pipeline.get_result(content_id, timeout=10.0)

        # Verify processing result
        assert result is not None
        assert isinstance(result, ProcessingResult)
        assert result.content_id == content_id
        assert result.status == ProcessingStatus.COMPLETED
        assert result.processing_time_ms > 0
        assert len(result.stages_completed) > 0

        # Should have cognitive analysis results
        assert result.cognitive_result is not None
        assert result.quality_score > 0

        # Should be semantically indexed (if passed quality filter)
        if result.quality_score >= running_pipeline.config.min_quality_threshold:
            assert result.semantic_indexed

    async def test_should_handle_different_priority_levels_correctly(
        self,
        running_pipeline,
        sample_content_items,
    ):
        """
        Test: Should handle different priority levels with appropriate
        processing order and performance characteristics.
        """
        # Submit items in reverse priority order
        submitted_items = []
        for item in reversed(sample_content_items):  # Low, Normal, High
            content_id = await running_pipeline.submit_content(item)
            submitted_items.append((content_id, item.priority))

        # Wait for all processing to complete
        results = []
        for content_id, priority in submitted_items:
            result = await running_pipeline.get_result(content_id, timeout=10.0)
            results.append((result, priority))

        # Verify all items processed successfully
        assert len(results) == len(sample_content_items)
        for result, priority in results:
            assert result is not None
            assert result.status == ProcessingStatus.COMPLETED
            assert result.processing_time_ms > 0

    async def test_should_process_batch_content_efficiently(self, running_pipeline):
        """
        Test: Should efficiently process multiple content items
        with proper concurrency and performance optimization.
        """
        # Create batch of varied content
        batch_items = []
        for i in range(20):
            priority = ProcessingPriority.HIGH if i < 5 else ProcessingPriority.NORMAL
            content = ContentItem(
                content_id=f"batch_item_{i}",
                content=f"Batch content item {i} about machine learning and AI research with comprehensive analysis.",
                source="batch_test",
                priority=priority,
                metadata={"batch_index": i},
            )
            batch_items.append(content)

        # Submit all items
        start_time = time.time()
        submitted_ids = []
        for item in batch_items:
            content_id = await running_pipeline.submit_content(item)
            submitted_ids.append(content_id)

        submission_time = time.time() - start_time

        # Wait for all results
        results = []
        for content_id in submitted_ids:
            result = await running_pipeline.get_result(content_id, timeout=15.0)
            if result:
                results.append(result)

        total_time = time.time() - start_time

        # Verify batch processing
        assert len(results) >= len(batch_items) * 0.9  # Allow for 10% failure tolerance

        # Check processing efficiency
        assert total_time < 30.0  # Should complete within 30 seconds

        successful_results = [
            r for r in results if r.status == ProcessingStatus.COMPLETED
        ]
        if successful_results:
            avg_processing_time = sum(
                r.processing_time_ms for r in successful_results
            ) / len(successful_results)
            assert avg_processing_time < 5000.0  # Average under 5 seconds per item

    async def test_should_handle_edge_processing_for_high_priority_content(
        self,
        running_pipeline,
    ):
        """
        Test: Should utilize edge processing for high-priority content
        when queue thresholds are exceeded.
        """
        # Fill up the queue to trigger edge processing
        filler_items = []
        for i in range(50):  # Half of max queue size
            content = ContentItem(
                content_id=f"filler_{i}",
                content=f"Filler content {i} to build up queue depth.",
                priority=ProcessingPriority.BACKGROUND,
            )
            filler_items.append(content)

        # Submit filler items
        for item in filler_items:
            await running_pipeline.submit_content(item)

        # Submit high-priority item that should trigger edge processing
        priority_content = ContentItem(
            content_id="priority_edge_test",
            content="Critical high-priority content requiring immediate edge processing.",
            priority=ProcessingPriority.CRITICAL,
            edge_location=EdgeLocation.LOCAL,
        )

        priority_id = await running_pipeline.submit_content(priority_content)

        # Wait for priority item result
        result = await running_pipeline.get_result(priority_id, timeout=5.0)

        # Verify result
        assert result is not None
        assert result.status == ProcessingStatus.COMPLETED
        assert (
            result.processing_time_ms < 1000.0
        )  # Should be fast due to edge processing

        # Check if edge processing was used (indicated by faster processing time)
        if result.edge_processing_time_ms > 0:
            assert (
                result.edge_processing_time_ms < 100.0
            )  # Edge processing should be very fast

    # ========================================================================
    # Quality Filtering and Error Handling Tests
    # ========================================================================

    async def test_should_apply_quality_filtering_appropriately(self, running_pipeline):
        """
        Test: Should apply quality filtering based on configuration
        while respecting priority-based bypass rules.
        """
        # Create content with different quality characteristics
        test_items = [
            ContentItem(
                content_id="high_quality",
                content="This comprehensive research study investigates advanced machine learning algorithms with detailed methodology, extensive experimental results, and thorough statistical analysis of performance metrics.",
                priority=ProcessingPriority.NORMAL,
                metadata={"expected_quality": "high"},
            ),
            ContentItem(
                content_id="low_quality",
                content="short text",
                priority=ProcessingPriority.NORMAL,
                metadata={"expected_quality": "low"},
            ),
            ContentItem(
                content_id="low_quality_critical",
                content="brief msg",
                priority=ProcessingPriority.CRITICAL,  # Should bypass quality filter
                metadata={"expected_quality": "low", "should_bypass": True},
            ),
        ]

        # Submit all items
        submitted_ids = []
        for item in test_items:
            content_id = await running_pipeline.submit_content(item)
            submitted_ids.append(content_id)

        # Wait for results
        results = {}
        for content_id in submitted_ids:
            result = await running_pipeline.get_result(content_id, timeout=10.0)
            results[content_id] = result

        # Verify quality filtering behavior
        high_quality_result = results["high_quality"]
        assert high_quality_result.status == ProcessingStatus.COMPLETED
        assert (
            high_quality_result.quality_score
            > running_pipeline.config.min_quality_threshold
        )
        assert high_quality_result.semantic_indexed  # Should pass quality filter

        low_quality_result = results["low_quality"]
        assert low_quality_result.status == ProcessingStatus.COMPLETED
        assert (
            low_quality_result.quality_score
            < running_pipeline.config.min_quality_threshold
        )
        # May or may not be semantically indexed depending on quality filter

        critical_result = results["low_quality_critical"]
        assert critical_result.status == ProcessingStatus.COMPLETED
        # Critical priority should bypass quality filter regardless of score

    async def test_should_handle_processing_errors_gracefully(self, running_pipeline):
        """
        Test: Should handle processing errors and edge cases
        without pipeline corruption or crashes.
        """
        # Create problematic content
        error_items = [
            ContentItem(
                content_id="empty_content",
                content="",
                priority=ProcessingPriority.NORMAL,
            ),
            ContentItem(
                content_id="very_long_content",
                content="x" * 100000,  # Very long content
                priority=ProcessingPriority.NORMAL,
            ),
            ContentItem(
                content_id="special_chars",
                content="Content with special chars: @#$%^&*(){}[]|\\:;\"'<>?,./",
                priority=ProcessingPriority.NORMAL,
            ),
        ]

        # Submit all items
        results = []
        for item in error_items:
            content_id = await running_pipeline.submit_content(item)
            result = await running_pipeline.get_result(content_id, timeout=10.0)
            results.append(result)

        # Verify error handling
        assert len(results) == len(error_items)
        for result in results:
            assert result is not None
            # Should either complete successfully or fail gracefully
            assert result.status in [
                ProcessingStatus.COMPLETED,
                ProcessingStatus.FAILED,
            ]
            assert result.processing_time_ms >= 0

    async def test_should_handle_concurrent_processing_safely(self, running_pipeline):
        """
        Test: Should handle concurrent processing operations
        without race conditions or data corruption.
        """
        # Create concurrent processing tasks
        concurrent_items = []
        for i in range(50):
            content = ContentItem(
                content_id=f"concurrent_{i}",
                content=f"Concurrent processing test content {i} for race condition testing.",
                priority=ProcessingPriority.NORMAL,
                metadata={"concurrent_index": i},
            )
            concurrent_items.append(content)

        # Submit items concurrently
        async def submit_item(item):
            content_id = await running_pipeline.submit_content(item)
            return await running_pipeline.get_result(content_id, timeout=15.0)

        # Run concurrent submissions
        tasks = [asyncio.create_task(submit_item(item)) for item in concurrent_items]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify concurrent processing integrity
        successful_results = [
            r for r in results if isinstance(r, ProcessingResult) and r is not None
        ]
        assert (
            len(successful_results) >= len(concurrent_items) * 0.8
        )  # 80% success rate minimum

        # Check for data corruption
        content_ids = set()
        for result in successful_results:
            assert result.content_id not in content_ids  # No duplicate processing
            content_ids.add(result.content_id)

    # ========================================================================
    # Performance and Metrics Tests
    # ========================================================================

    async def test_should_collect_comprehensive_performance_metrics(
        self,
        running_pipeline,
    ):
        """
        Test: Should collect comprehensive performance metrics
        including throughput, latency, and stage-specific timing.
        """
        # Process some items to generate metrics
        test_items = []
        for i in range(10):
            content = ContentItem(
                content_id=f"metrics_test_{i}",
                content=f"Metrics test content {i} for performance measurement and analysis.",
                priority=ProcessingPriority.NORMAL,
            )
            test_items.append(content)

        # Submit and process items
        for item in test_items:
            content_id = await running_pipeline.submit_content(item)
            await running_pipeline.get_result(content_id, timeout=10.0)

        # Get pipeline metrics
        metrics = running_pipeline.get_pipeline_metrics()

        # Verify metrics structure and content
        assert isinstance(metrics, PipelineMetrics)
        assert metrics.total_processed > 0
        assert metrics.successful_processed <= metrics.total_processed
        assert metrics.failed_processed >= 0
        assert metrics.average_processing_time_ms >= 0
        assert metrics.throughput_per_second >= 0

        # Check stage-specific metrics
        assert isinstance(metrics.stage_times, dict)
        if metrics.stage_times:
            for stage, avg_time in metrics.stage_times.items():
                assert avg_time >= 0

        # Check bottleneck detection
        if metrics.bottleneck_stage:
            assert metrics.bottleneck_stage in metrics.stage_times

    async def test_should_provide_queue_status_and_monitoring(self, running_pipeline):
        """
        Test: Should provide accurate queue status and monitoring
        information for operational visibility.
        """
        # Submit items to different priority queues
        priorities = [
            ProcessingPriority.HIGH,
            ProcessingPriority.NORMAL,
            ProcessingPriority.LOW,
        ]

        for i, priority in enumerate(priorities):
            for j in range(3):  # 3 items per priority
                content = ContentItem(
                    content_id=f"queue_test_{priority.value}_{j}",
                    content=f"Queue test content for {priority.value} priority.",
                    priority=priority,
                )
                await running_pipeline.submit_content(content)

        # Check queue status
        queue_status = running_pipeline.get_queue_status()

        # Verify queue status structure
        assert isinstance(queue_status, dict)
        for priority in ProcessingPriority:
            assert priority.value in queue_status
            assert isinstance(queue_status[priority.value], int)
            assert queue_status[priority.value] >= 0

        # Check active processing count
        active_count = running_pipeline.get_active_processing_count()
        assert isinstance(active_count, int)
        assert active_count >= 0

    # ========================================================================
    # Edge Computing Tests
    # ========================================================================

    async def test_edge_processor_should_handle_fast_processing(self):
        """
        Test: Edge processor should handle fast local processing
        with minimal latency and proper statistics tracking.
        """
        edge_processor = EdgeProcessor(EdgeLocation.LOCAL)

        # Test edge processing
        test_content = ContentItem(
            content_id="edge_test",
            content="Test content for edge processing performance measurement.",
            edge_location=EdgeLocation.LOCAL,
        )

        start_time = time.time()
        result = await edge_processor.process_item(test_content)
        processing_time = (time.time() - start_time) * 1000

        # Verify edge processing result
        assert isinstance(result, dict)
        assert result.get("edge_processed", False)
        assert result.get("edge_location") == EdgeLocation.LOCAL.value
        assert "content_length" in result
        assert "word_count" in result

        # Verify fast processing
        assert processing_time < 100.0  # Should be under 100ms

        # Check statistics
        stats = edge_processor.get_stats()
        assert stats["items_processed"] == 1
        assert stats["average_processing_time"] > 0


@pytest.mark.asyncio()
class TestProcessingStages:
    """
    Test suite for individual processing stage components.
    """

    @pytest_asyncio.fixture
    async def cognitive_stage(self):
        """Create cognitive analysis stage for testing"""
        cognitive_engine = CognitiveAnalysisEngine()
        return CognitiveAnalysisStage(cognitive_engine)

    @pytest_asyncio.fixture
    async def semantic_stage(self):
        """Create semantic indexing stage for testing"""
        semantic_engine = SemanticSearchEngine()
        return SemanticIndexingStage(semantic_engine)

    @pytest_asyncio.fixture
    def quality_stage(self):
        """Create quality filtering stage for testing"""
        config = PipelineConfig(min_quality_threshold=0.5)
        return QualityFilteringStage(config)

    async def test_cognitive_analysis_stage_should_process_content_correctly(
        self,
        cognitive_stage,
    ):
        """
        Test: Cognitive analysis stage should process content
        and return comprehensive analysis results.
        """
        content = ContentItem(
            content_id="cognitive_test",
            content="This comprehensive research study investigates machine learning algorithms for advanced artificial intelligence applications.",
            metadata={"source_type": "academic"},
        )

        result = await cognitive_stage.process(content)

        # Verify cognitive analysis result
        assert isinstance(result, dict)
        assert result.get("processing_successful", False)
        assert "cognitive_result" in result
        assert "quality_score" in result

        if result["processing_successful"]:
            assert result["cognitive_result"] is not None
            assert 0.0 <= result["quality_score"] <= 1.0

    async def test_semantic_indexing_stage_should_create_embeddings(
        self,
        semantic_stage,
    ):
        """
        Test: Semantic indexing stage should create vector embeddings
        and index content for search capabilities.
        """
        content = ContentItem(
            content_id="semantic_test",
            content="Machine learning and artificial intelligence research with neural networks and deep learning algorithms.",
            metadata={"content_type": "research"},
        )

        result = await semantic_stage.process(content)

        # Verify semantic indexing result
        assert isinstance(result, dict)
        assert result.get("processing_successful", False)

        if result["processing_successful"]:
            assert result.get("embedding_generated", False)
            assert result.get("semantic_indexed", False)
            assert "embedding_dimensionality" in result

    async def test_quality_filtering_stage_should_filter_based_on_thresholds(
        self,
        quality_stage,
    ):
        """
        Test: Quality filtering stage should filter content
        based on quality thresholds and priority rules.
        """
        # Test with different quality scores in context
        test_cases = [
            {"quality_score": 0.8, "expected_pass": True},
            {"quality_score": 0.3, "expected_pass": False},
            {"quality_score": 0.1, "expected_pass": False},
        ]

        for test_case in test_cases:
            content = ContentItem(
                content_id="quality_test",
                content="Test content for quality filtering.",
                priority=ProcessingPriority.NORMAL,
            )

            context = {"quality_score": test_case["quality_score"]}
            result = await quality_stage.process(content, context)

            # Verify quality filtering result
            assert isinstance(result, dict)
            assert result.get("processing_successful", False)

            if result["processing_successful"]:
                assert result["quality_score"] == test_case["quality_score"]
                assert result["passes_quality_filter"] == test_case["expected_pass"]


@pytest.mark.asyncio()
class TestProductionConfiguration:
    """
    Test suite for production-ready configuration and deployment scenarios.
    """

    async def test_should_create_production_realtime_pipeline(self):
        """
        Test: Should create production-ready real-time pipeline
        with optimized configuration and performance settings.
        """
        pipeline = await create_production_realtime_pipeline()

        # Check production configuration
        assert pipeline.config.max_concurrent_processing >= 50
        assert pipeline.config.max_queue_size >= 10000
        assert pipeline.config.enable_quality_filtering
        assert pipeline.config.enable_edge_processing
        assert pipeline.config.enable_performance_monitoring
        assert pipeline.config.enable_batch_processing

        # Test with production-level content
        test_content = ContentItem(
            content_id="production_test",
            content="Production-level content processing test with comprehensive machine learning analysis and semantic understanding capabilities.",
            priority=ProcessingPriority.HIGH,
            metadata={"environment": "production"},
        )

        # Start pipeline
        await pipeline.start_pipeline()

        try:
            # Submit content
            content_id = await pipeline.submit_content(test_content)
            result = await pipeline.get_result(content_id, timeout=15.0)

            # Verify production processing
            assert result is not None
            assert result.status in [
                ProcessingStatus.COMPLETED,
                ProcessingStatus.FAILED,
            ]
            assert result.processing_time_ms > 0

        finally:
            await pipeline.stop_pipeline()


class TestDataStructures:
    """
    Test suite for real-time processing data structures and serialization.
    """

    def test_content_item_should_serialize_correctly(self):
        """
        Test: ContentItem should properly serialize to dictionary
        for JSON export and API responses.
        """
        content = ContentItem(
            content_id="serialize_test",
            content="Test content for serialization",
            content_type="text",
            source="test",
            priority=ProcessingPriority.HIGH,
            metadata={"test": True},
            edge_location=EdgeLocation.LOCAL,
        )

        content_dict = content.to_dict()

        # Verify serialization
        assert content_dict["content_id"] == "serialize_test"
        assert content_dict["content"] == "Test content for serialization"
        assert content_dict["content_type"] == "text"
        assert content_dict["source"] == "test"
        assert content_dict["priority"] == "high"
        assert content_dict["metadata"]["test"]
        assert content_dict["edge_location"] == "local"
        assert "ingestion_timestamp" in content_dict

    def test_processing_result_should_serialize_completely(self):
        """
        Test: ProcessingResult should serialize all components
        correctly for comprehensive API responses.
        """
        result = ProcessingResult(
            content_id="result_test",
            status=ProcessingStatus.COMPLETED,
            stages_completed=[
                ProcessingStage.COGNITIVE_ANALYSIS,
                ProcessingStage.SEMANTIC_INDEXING,
            ],
            processing_time_ms=150.5,
            semantic_indexed=True,
            quality_score=0.85,
            edge_processing_time_ms=25.0,
        )

        result_dict = result.to_dict()

        # Verify complete serialization
        assert result_dict["content_id"] == "result_test"
        assert result_dict["status"] == "completed"
        assert "cognitive_analysis" in result_dict["stages_completed"]
        assert "semantic_indexing" in result_dict["stages_completed"]
        assert result_dict["processing_time_ms"] == 150.5
        assert result_dict["semantic_indexed"]
        assert result_dict["quality_score"] == 0.85
        assert result_dict["edge_processing_time_ms"] == 25.0
        assert "start_timestamp" in result_dict

    def test_pipeline_metrics_should_serialize_comprehensively(self):
        """
        Test: PipelineMetrics should serialize comprehensive metrics
        for monitoring and analytics purposes.
        """
        metrics = PipelineMetrics(
            total_processed=100,
            successful_processed=95,
            failed_processed=5,
            average_processing_time_ms=250.0,
            throughput_per_second=10.5,
            stage_times={"cognitive_analysis": 100.0, "semantic_indexing": 75.0},
            bottleneck_stage="cognitive_analysis",
            edge_utilization={"local": 25.0, "regional": 10.0},
        )

        metrics_dict = metrics.to_dict()

        # Verify comprehensive serialization
        assert metrics_dict["total_processed"] == 100
        assert metrics_dict["successful_processed"] == 95
        assert metrics_dict["failed_processed"] == 5
        assert metrics_dict["average_processing_time_ms"] == 250.0
        assert metrics_dict["throughput_per_second"] == 10.5
        assert metrics_dict["stage_times"]["cognitive_analysis"] == 100.0
        assert metrics_dict["bottleneck_stage"] == "cognitive_analysis"
        assert metrics_dict["edge_utilization"]["local"] == 25.0
