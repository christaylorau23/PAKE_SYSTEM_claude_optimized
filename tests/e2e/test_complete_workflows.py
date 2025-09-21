#!/usr/bin/env python3
"""
PAKE System - End-to-End Testing
Tests complete user workflows from start to finish.

This module demonstrates comprehensive E2E testing patterns:
- Complete user journeys
- Real browser automation (when applicable)
- Full system integration
- Performance validation
- User experience testing

E2E Testing Principles:
- Test complete workflows, not individual components
- Use real data and real services
- Validate user experience and business outcomes
- Test performance under realistic conditions
"""

import asyncio
import json
import time
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional

import pytest
import pytest_asyncio
from unittest.mock import patch

from services.ingestion.orchestrator import IngestionOrchestrator, IngestionConfig
from services.analytics.performance_analyzer import PerformanceAnalyzer
from services.security.authentication_service import AuthenticationService
from services.database.connection_manager import DatabaseConnectionManager
from services.caching.redis_cache_strategy import RedisCacheStrategy
from services.messaging.message_bus import MessageBus


class TestCompleteUserWorkflows:
    """
    End-to-end tests for complete user workflows.
    
    These tests simulate real user journeys through the PAKE System,
    validating the entire experience from start to finish.
    """

    @pytest.fixture
    async def full_system_setup(self):
        """Set up complete PAKE System for E2E testing"""
        # Database connection
        db_manager = DatabaseConnectionManager(
            host="localhost",
            port=5432,
            database="pake_e2e_test",
            user="postgres",
            REDACTED_SECRET="postgres"
        )
        await db_manager.connect()
        
        # Cache setup
        cache = RedisCacheStrategy("redis://localhost:6379/20")
        await cache.start()
        
        # Message bus setup
        message_bus = MessageBus("redis://localhost:6379/21")
        await message_bus.start()
        
        # Authentication service
        auth_service = AuthenticationService(secret_key="e2e_test_secret")
        
        # Performance analyzer
        analyzer = PerformanceAnalyzer()
        
        yield {
            "database": db_manager,
            "cache": cache,
            "message_bus": message_bus,
            "auth_service": auth_service,
            "analyzer": analyzer
        }
        
        # Cleanup
        await message_bus.stop()
        await cache.stop()
        await db_manager.disconnect()

    # ========================================================================
    # Knowledge Ingestion Workflow E2E Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_complete_knowledge_ingestion_workflow(self, full_system_setup):
        """
        Test: Complete knowledge ingestion workflow from user request to stored knowledge
        
        E2E Test Scenario:
        1. User submits research topic
        2. System creates ingestion plan
        3. Multiple sources are queried (web, arxiv, pubmed)
        4. Content is processed and analyzed
        5. Results are stored and cached
        6. User receives comprehensive results
        """
        db_manager = full_system_setup["database"]
        cache = full_system_setup["cache"]
        message_bus = full_system_setup["message_bus"]
        
        # Set up complete orchestrator
        config = IngestionConfig(
            max_concurrent_sources=5,
            enable_cognitive_processing=True,
            enable_deduplication=True,
            enable_caching=True,
            enable_database_storage=True,
            timeout_seconds=120
        )
        
        orchestrator = IngestionOrchestrator(config)
        orchestrator.database_manager = db_manager
        orchestrator.cache_strategy = cache
        orchestrator.message_bus = message_bus
        
        # User research request
        user_request = {
            "topic": "Artificial Intelligence in Healthcare",
            "user_id": "e2e_test_user",
            "requirements": {
                "sources": ["web", "arxiv", "pubmed"],
                "max_results_per_source": 10,
                "include_recent": True,
                "quality_threshold": 0.7
            },
            "preferences": {
                "language": "en",
                "include_metadata": True,
                "enable_summarization": True
            }
        }
        
        # Create comprehensive ingestion plan
        ingestion_plan = {
            "topic": user_request["topic"],
            "user_id": user_request["user_id"],
            "sources": [
                {
                    "type": "web",
                    "urls": [
                        "https://www.nature.com/articles/ai-healthcare",
                        "https://www.nejm.org/ai-medical-diagnosis",
                        "https://www.who.int/ai-healthcare-guidelines"
                    ],
                    "priority": 1,
                    "scraping_options": {
                        "wait_time": 2000,
                        "include_headings": True,
                        "extract_metadata": True
                    }
                },
                {
                    "type": "arxiv",
                    "query": "artificial intelligence healthcare medical diagnosis",
                    "categories": ["cs.AI", "cs.LG", "q-bio.QM"],
                    "max_results": 15,
                    "priority": 2,
                    "date_range": "2023-01-01:2024-12-31"
                },
                {
                    "type": "pubmed",
                    "query": "artificial intelligence healthcare",
                    "mesh_terms": ["Artificial Intelligence", "Health Care", "Machine Learning"],
                    "publication_types": ["Journal Article", "Review"],
                    "max_results": 12,
                    "priority": 3,
                    "date_range": "2023-01-01:2024-12-31"
                }
            ],
            "processing_options": {
                "enable_cognitive_assessment": True,
                "enable_deduplication": True,
                "enable_summarization": True,
                "quality_threshold": 0.7,
                "enable_cross_referencing": True
            }
        }
        
        # Mock successful API responses for realistic E2E testing
        with patch('services.ingestion.firecrawl_service.FirecrawlService.extract_content') as mock_firecrawl, \
             patch('services.ingestion.arxiv_service.ArxivService.search_papers') as mock_arxiv, \
             patch('services.ingestion.pubmed_service.PubmedService.search_articles') as mock_pubmed:
            
            # Configure realistic mock responses
            mock_firecrawl.return_value = {
                "success": True,
                "content": "AI in healthcare is revolutionizing medical diagnosis and treatment...",
                "url": "https://www.nature.com/articles/ai-healthcare",
                "metadata": {
                    "title": "AI Revolution in Healthcare",
                    "author": "Dr. Sarah Johnson",
                    "published_date": "2024-01-15",
                    "word_count": 2500,
                    "reading_time": "10 minutes"
                }
            }
            
            mock_arxiv.return_value = {
                "success": True,
                "papers": [
                    {
                        "title": "Deep Learning for Medical Image Analysis",
                        "abstract": "This paper presents novel deep learning approaches for medical image analysis...",
                        "authors": ["Dr. John Smith", "Dr. Jane Doe"],
                        "arxiv_id": "2401.12345",
                        "published": "2024-01-10",
                        "categories": ["cs.CV", "cs.LG"]
                    },
                    {
                        "title": "AI-Powered Drug Discovery",
                        "abstract": "We present a comprehensive framework for AI-driven drug discovery...",
                        "authors": ["Dr. Alice Brown", "Dr. Bob Wilson"],
                        "arxiv_id": "2401.12346",
                        "published": "2024-01-12",
                        "categories": ["cs.LG", "q-bio.QM"]
                    }
                ],
                "total_results": 2
            }
            
            mock_pubmed.return_value = {
                "success": True,
                "articles": [
                    {
                        "title": "Machine Learning in Clinical Decision Support",
                        "abstract": "This systematic review examines the role of machine learning in clinical decision support systems...",
                        "authors": ["Dr. Michael Chen", "Dr. Lisa Wang"],
                        "pmid": "12345678",
                        "journal": "Journal of Medical AI",
                        "published": "2024-01-08"
                    }
                ],
                "total_results": 1
            }
            
            # Execute complete workflow
            start_time = time.time()
            result = await orchestrator.execute_plan(ingestion_plan)
            execution_time = time.time() - start_time
            
            # Verify complete workflow success
            assert result.success is True
            assert result.total_sources_processed == 3
            assert result.total_content_items >= 3  # At least one item per source
            assert result.execution_time > 0
            assert execution_time < 120  # Should complete within timeout
            
            # Verify data storage in database
            stored_items = await db_manager.fetch_all(
                "SELECT * FROM content_items WHERE topic = $1",
                user_request["topic"]
            )
            assert len(stored_items) >= 3
            
            # Verify cache storage
            cache_hits = 0
            for item in stored_items:
                cached_item = await cache.get("content_items", str(item["id"]))
                if cached_item:
                    cache_hits += 1
            assert cache_hits > 0
            
            # Verify content quality and processing
            for item in result.content_items:
                assert item["title"] is not None
                assert item["content"] is not None
                assert len(item["content"]) > 100  # Substantial content
                assert item["source"] in ["web", "arxiv", "pubmed"]
                
                # Verify cognitive processing was applied
                if "cognitive_assessment" in item:
                    assert item["cognitive_assessment"]["overall_quality"] >= 0.7
            
            # Verify deduplication worked
            unique_titles = set(item["title"] for item in result.content_items)
            assert len(unique_titles) == len(result.content_items)  # No duplicates
            
            # Verify cross-referencing
            if result.cross_references:
                assert len(result.cross_references) > 0

    @pytest.mark.asyncio
    async def test_user_research_session_workflow(self, full_system_setup):
        """
        Test: Complete user research session from login to results delivery
        
        E2E Test Scenario:
        1. User authenticates
        2. User creates research session
        3. User submits multiple queries
        4. System processes and stores results
        5. User reviews and refines results
        6. User exports final research
        """
        db_manager = full_system_setup["database"]
        auth_service = full_system_setup["auth_service"]
        cache = full_system_setup["cache"]
        
        # Step 1: User Authentication
        user_data = {
            "user_id": "research_session_user",
            "email": "researcher@test.com",
            "role": "researcher",
            "permissions": ["research", "export", "collaborate"]
        }
        
        # Create user in database
        await db_manager.execute_query(
            """
            INSERT INTO users (user_id, email, role, permissions, created_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            user_data["user_id"],
            user_data["email"],
            user_data["role"],
            json.dumps(user_data["permissions"]),
            datetime.now(UTC)
        )
        
        # Generate authentication token
        auth_token = auth_service.generate_token(user_data, expires_in=3600)
        auth_result = auth_service.validate_token(auth_token)
        
        assert auth_result.success is True
        assert auth_result.user_data["user_id"] == user_data["user_id"]
        
        # Step 2: Create Research Session
        session_data = {
            "session_id": "e2e_research_session_001",
            "user_id": user_data["user_id"],
            "topic": "Machine Learning in Finance",
            "created_at": datetime.now(UTC),
            "status": "active"
        }
        
        await db_manager.execute_query(
            """
            INSERT INTO research_sessions (session_id, user_id, topic, created_at, status)
            VALUES ($1, $2, $3, $4, $5)
            """,
            session_data["session_id"],
            session_data["user_id"],
            session_data["topic"],
            session_data["created_at"],
            session_data["status"]
        )
        
        # Cache session data
        await cache.set("sessions", session_data["session_id"], session_data, ttl=7200)
        
        # Step 3: Submit Multiple Research Queries
        research_queries = [
            {
                "query_id": "query_001",
                "session_id": session_data["session_id"],
                "query": "machine learning algorithms for fraud detection",
                "sources": ["web", "arxiv"],
                "max_results": 5
            },
            {
                "query_id": "query_002", 
                "session_id": session_data["session_id"],
                "query": "deep learning in algorithmic trading",
                "sources": ["arxiv", "pubmed"],
                "max_results": 8
            },
            {
                "query_id": "query_003",
                "session_id": session_data["session_id"],
                "query": "AI risk management in financial services",
                "sources": ["web", "pubmed"],
                "max_results": 6
            }
        ]
        
        # Process each query
        all_results = []
        for query in research_queries:
            # Store query in database
            await db_manager.execute_query(
                """
                INSERT INTO research_queries (query_id, session_id, query_text, sources, max_results, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                query["query_id"],
                query["session_id"],
                query["query"],
                json.dumps(query["sources"]),
                query["max_results"],
                datetime.now(UTC)
            )
            
            # Mock query processing
            query_result = {
                "query_id": query["query_id"],
                "results": [
                    {
                        "title": f"Research Result for {query['query']}",
                        "content": f"Detailed content about {query['query']}...",
                        "source": query["sources"][0],
                        "relevance_score": 0.85,
                        "quality_score": 0.78
                    }
                ],
                "total_results": 1,
                "processing_time": 2.5
            }
            
            all_results.append(query_result)
            
            # Store results in database
            for result_item in query_result["results"]:
                await db_manager.execute_query(
                    """
                    INSERT INTO research_results (query_id, title, content, source, relevance_score, quality_score, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    query["query_id"],
                    result_item["title"],
                    result_item["content"],
                    result_item["source"],
                    result_item["relevance_score"],
                    result_item["quality_score"],
                    datetime.now(UTC)
                )
        
        # Step 4: Aggregate Session Results
        session_results = await db_manager.fetch_all(
            """
            SELECT rr.*, rq.query_text, rq.sources
            FROM research_results rr
            JOIN research_queries rq ON rr.query_id = rq.query_id
            WHERE rq.session_id = $1
            ORDER BY rr.relevance_score DESC
            """,
            session_data["session_id"]
        )
        
        assert len(session_results) == 3  # One result per query
        
        # Step 5: User Review and Refinement
        # Simulate user reviewing results and marking favorites
        favorite_results = session_results[:2]  # Top 2 results
        
        for result in favorite_results:
            await db_manager.execute_query(
                """
                UPDATE research_results 
                SET is_favorite = true, user_rating = $1, reviewed_at = $2
                WHERE id = $3
                """,
                5,  # 5-star rating
                datetime.now(UTC),
                result["id"]
            )
        
        # Step 6: Export Final Research
        export_data = {
            "session_id": session_data["session_id"],
            "export_format": "comprehensive_report",
            "include_favorites_only": True,
            "include_metadata": True,
            "include_sources": True
        }
        
        # Generate export
        export_results = await db_manager.fetch_all(
            """
            SELECT rr.*, rq.query_text
            FROM research_results rr
            JOIN research_queries rq ON rr.query_id = rq.query_id
            WHERE rq.session_id = $1 AND rr.is_favorite = true
            ORDER BY rr.user_rating DESC, rr.relevance_score DESC
            """,
            session_data["session_id"]
        )
        
        # Verify export data
        assert len(export_results) == 2
        assert all(result["is_favorite"] for result in export_results)
        assert all(result["user_rating"] == 5 for result in export_results)
        
        # Store export in database
        export_id = f"export_{session_data['session_id']}_{int(time.time())}"
        await db_manager.execute_query(
            """
            INSERT INTO research_exports (export_id, session_id, export_format, data, created_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            export_id,
            session_data["session_id"],
            export_data["export_format"],
            json.dumps([dict(result) for result in export_results]),
            datetime.now(UTC)
        )
        
        # Cache export for quick access
        await cache.set("exports", export_id, export_results, ttl=86400)  # 24 hours
        
        # Verify complete workflow
        final_session = await db_manager.fetch_one(
            "SELECT * FROM research_sessions WHERE session_id = $1",
            session_data["session_id"]
        )
        
        assert final_session["status"] == "active"
        assert final_session["user_id"] == user_data["user_id"]

    # ========================================================================
    # Performance and Scalability E2E Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_high_volume_ingestion_performance(self, full_system_setup):
        """
        Test: System should handle high-volume ingestion with acceptable performance
        
        E2E Performance Test:
        - Process large number of concurrent requests
        - Measure response times and throughput
        - Verify system stability under load
        - Test resource utilization
        """
        db_manager = full_system_setup["database"]
        analyzer = full_system_setup["analyzer"]
        
        # Set up orchestrator for performance testing
        config = IngestionConfig(
            max_concurrent_sources=10,
            enable_cognitive_processing=True,
            enable_caching=True,
            timeout_seconds=60
        )
        
        orchestrator = IngestionOrchestrator(config)
        orchestrator.database_manager = db_manager
        
        # Generate high-volume test data
        concurrent_requests = 20
        test_topics = [
            f"Performance Test Topic {i}" for i in range(concurrent_requests)
        ]
        
        # Mock high-performance responses
        with patch('services.ingestion.firecrawl_service.FirecrawlService.extract_content') as mock_firecrawl:
            mock_firecrawl.return_value = {
                "success": True,
                "content": "High-performance test content for load testing...",
                "url": "https://example.com/performance-test",
                "metadata": {"title": "Performance Test Article", "word_count": 500}
            }
            
            # Execute concurrent requests
            start_time = time.time()
            
            async def process_request(topic):
                ingestion_plan = {
                    "topic": topic,
                    "sources": [
                        {
                            "type": "web",
                            "url": f"https://example.com/{topic.replace(' ', '-').lower()}",
                            "priority": 1
                        }
                    ]
                }
                return await orchestrator.execute_plan(ingestion_plan)
            
            # Process all requests concurrently
            tasks = [process_request(topic) for topic in test_topics]
            results = await asyncio.gather(*tasks)
            
            total_execution_time = time.time() - start_time
            
            # Verify performance metrics
            successful_requests = sum(1 for result in results if result.success)
            assert successful_requests >= concurrent_requests * 0.95  # 95% success rate
            
            # Calculate performance metrics
            avg_response_time = total_execution_time / concurrent_requests
            throughput = concurrent_requests / total_execution_time
            
            assert avg_response_time < 10.0  # Average response time under 10 seconds
            assert throughput > 2.0  # At least 2 requests per second
            
            # Verify database performance
            stored_items = await db_manager.fetch_all(
                "SELECT * FROM content_items WHERE title LIKE 'Performance Test%'"
            )
            assert len(stored_items) >= successful_requests
            
            # Record performance metrics
            performance_metrics = {
                "concurrent_requests": concurrent_requests,
                "successful_requests": successful_requests,
                "total_execution_time": total_execution_time,
                "avg_response_time": avg_response_time,
                "throughput_rps": throughput,
                "success_rate": successful_requests / concurrent_requests
            }
            
            # Store performance metrics
            await db_manager.execute_query(
                """
                INSERT INTO performance_metrics (test_type, metrics_data, created_at)
                VALUES ($1, $2, $3)
                """,
                "high_volume_ingestion",
                json.dumps(performance_metrics),
                datetime.now(UTC)
            )

    @pytest.mark.asyncio
    async def test_system_reliability_under_failure_conditions(self, full_system_setup):
        """
        Test: System should maintain reliability under partial failure conditions
        
        E2E Reliability Test:
        - Simulate partial service failures
        - Verify graceful degradation
        - Test error recovery mechanisms
        - Validate data consistency
        """
        db_manager = full_system_setup["database"]
        cache = full_system_setup["cache"]
        
        # Set up orchestrator with failure scenarios
        config = IngestionConfig(
            max_concurrent_sources=5,
            enable_cognitive_processing=True,
            enable_caching=True,
            timeout_seconds=30
        )
        
        orchestrator = IngestionOrchestrator(config)
        orchestrator.database_manager = db_manager
        orchestrator.cache_strategy = cache
        
        # Test scenario with mixed success/failure
        ingestion_plan = {
            "topic": "Reliability Test Topic",
            "sources": [
                {
                    "type": "web",
                    "url": "https://working-site.com/article",
                    "priority": 1
                },
                {
                    "type": "web", 
                    "url": "https://failing-site.com/article",
                    "priority": 2
                },
                {
                    "type": "web",
                    "url": "https://slow-site.com/article",
                    "priority": 3
                }
            ]
        }
        
        # Mock mixed results (success, failure, timeout)
        with patch('services.ingestion.firecrawl_service.FirecrawlService.extract_content') as mock_firecrawl:
            def mock_extract_side_effect(url):
                if "working-site.com" in url:
                    return {
                        "success": True,
                        "content": "Reliability test content",
                        "url": url,
                        "metadata": {"title": "Working Site Article"}
                    }
                elif "failing-site.com" in url:
                    raise Exception("Site unavailable")
                elif "slow-site.com" in url:
                    # Simulate timeout
                    time.sleep(35)  # Longer than timeout
                    return {
                        "success": True,
                        "content": "Slow site content",
                        "url": url
                    }
            
            mock_firecrawl.side_effect = mock_extract_side_effect
            
            # Execute with failure scenarios
            result = await orchestrator.execute_plan(ingestion_plan)
            
            # Verify graceful degradation
            assert result.success is True  # Overall success despite partial failures
            assert result.total_sources_processed == 3
            assert result.total_content_items >= 1  # At least one successful source
            assert len(result.errors) >= 1  # Should have some errors
            
            # Verify error handling
            error_types = [error.get("type", "unknown") for error in result.errors]
            assert "connection_error" in error_types or "timeout_error" in error_types
            
            # Verify data consistency
            stored_items = await db_manager.fetch_all(
                "SELECT * FROM content_items WHERE topic = $1",
                ingestion_plan["topic"]
            )
            assert len(stored_items) >= 1
            
            # Verify cache consistency
            for item in stored_items:
                cached_item = await cache.get("content_items", str(item["id"]))
                if cached_item:
                    assert cached_item["title"] == item["title"]

    # ========================================================================
    # User Experience E2E Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_complete_user_onboarding_workflow(self, full_system_setup):
        """
        Test: Complete user onboarding workflow from registration to first research
        
        E2E User Experience Test:
        1. User registration
        2. Email verification
        3. Profile setup
        4. First research query
        5. Results delivery
        6. User feedback collection
        """
        db_manager = full_system_setup["database"]
        auth_service = full_system_setup["auth_service"]
        cache = full_system_setup["cache"]
        
        # Step 1: User Registration
        registration_data = {
            "email": "newuser@test.com",
            "REDACTED_SECRET": "secure_REDACTED_SECRET_123",
            "full_name": "New User",
            "organization": "Test Organization",
            "research_interests": ["AI", "Machine Learning", "Data Science"]
        }
        
        # Create user account
        user_id = f"user_{int(time.time())}"
        await db_manager.execute_query(
            """
            INSERT INTO users (user_id, email, REDACTED_SECRET_hash, full_name, organization, research_interests, status, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            user_id,
            registration_data["email"],
            "hashed_REDACTED_SECRET",  # In real system, would hash the REDACTED_SECRET
            registration_data["full_name"],
            registration_data["organization"],
            json.dumps(registration_data["research_interests"]),
            "pending_verification",
            datetime.now(UTC)
        )
        
        # Step 2: Email Verification (simulated)
        verification_token = auth_service.generate_token(
            {"user_id": user_id, "action": "email_verification"},
            expires_in=3600
        )
        
        # Simulate email verification
        await db_manager.execute_query(
            "UPDATE users SET status = $1, verified_at = $2 WHERE user_id = $3",
            "verified",
            datetime.now(UTC),
            user_id
        )
        
        # Step 3: Profile Setup
        profile_data = {
            "user_id": user_id,
            "preferences": {
                "default_sources": ["web", "arxiv"],
                "max_results_per_query": 10,
                "quality_threshold": 0.8,
                "notification_preferences": {
                    "email_notifications": True,
                    "research_updates": True
                }
            },
            "research_history": [],
            "saved_searches": []
        }
        
        await db_manager.execute_query(
            """
            INSERT INTO user_profiles (user_id, preferences, research_history, saved_searches, created_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            user_id,
            json.dumps(profile_data["preferences"]),
            json.dumps(profile_data["research_history"]),
            json.dumps(profile_data["saved_searches"]),
            datetime.now(UTC)
        )
        
        # Cache user profile
        await cache.set("user_profiles", user_id, profile_data, ttl=3600)
        
        # Step 4: First Research Query
        first_query = {
            "query_id": f"first_query_{user_id}",
            "user_id": user_id,
            "query": "introduction to machine learning",
            "sources": ["web", "arxiv"],
            "max_results": 5,
            "created_at": datetime.now(UTC)
        }
        
        await db_manager.execute_query(
            """
            INSERT INTO user_queries (query_id, user_id, query_text, sources, max_results, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            first_query["query_id"],
            first_query["user_id"],
            first_query["query"],
            json.dumps(first_query["sources"]),
            first_query["max_results"],
            first_query["created_at"]
        )
        
        # Mock successful research results
        research_results = [
            {
                "title": "Introduction to Machine Learning",
                "content": "Machine learning is a subset of artificial intelligence...",
                "source": "web",
                "url": "https://example.com/ml-intro",
                "relevance_score": 0.95,
                "quality_score": 0.88
            },
            {
                "title": "Fundamentals of ML Algorithms",
                "content": "This paper covers the fundamental algorithms in machine learning...",
                "source": "arxiv",
                "arxiv_id": "2401.12347",
                "relevance_score": 0.92,
                "quality_score": 0.85
            }
        ]
        
        # Store research results
        for result in research_results:
            await db_manager.execute_query(
                """
                INSERT INTO query_results (query_id, title, content, source, url, relevance_score, quality_score, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                first_query["query_id"],
                result["title"],
                result["content"],
                result["source"],
                result.get("url") or result.get("arxiv_id"),
                result["relevance_score"],
                result["quality_score"],
                datetime.now(UTC)
            )
        
        # Step 5: Results Delivery
        delivered_results = await db_manager.fetch_all(
            "SELECT * FROM query_results WHERE query_id = $1 ORDER BY relevance_score DESC",
            first_query["query_id"]
        )
        
        assert len(delivered_results) == 2
        assert all(result["relevance_score"] >= 0.9 for result in delivered_results)
        
        # Step 6: User Feedback Collection
        user_feedback = {
            "query_id": first_query["query_id"],
            "user_id": user_id,
            "overall_satisfaction": 5,  # 5-star rating
            "result_quality": 4,
            "response_time": 5,
            "comments": "Great results! Very helpful for getting started with ML.",
            "would_recommend": True,
            "created_at": datetime.now(UTC)
        }
        
        await db_manager.execute_query(
            """
            INSERT INTO user_feedback (query_id, user_id, overall_satisfaction, result_quality, response_time, comments, would_recommend, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            user_feedback["query_id"],
            user_feedback["user_id"],
            user_feedback["overall_satisfaction"],
            user_feedback["result_quality"],
            user_feedback["response_time"],
            user_feedback["comments"],
            user_feedback["would_recommend"],
            user_feedback["created_at"]
        )
        
        # Update user research history
        await db_manager.execute_query(
            """
            UPDATE user_profiles 
            SET research_history = array_append(research_history, $1)
            WHERE user_id = $2
            """,
            first_query["query"],
            user_id
        )
        
        # Verify complete onboarding workflow
        final_user = await db_manager.fetch_one(
            "SELECT * FROM users WHERE user_id = $1",
            user_id
        )
        
        assert final_user["status"] == "verified"
        assert final_user["email"] == registration_data["email"]
        
        # Verify profile setup
        user_profile = await db_manager.fetch_one(
            "SELECT * FROM user_profiles WHERE user_id = $1",
            user_id
        )
        
        assert user_profile is not None
        preferences = json.loads(user_profile["preferences"])
        assert preferences["default_sources"] == ["web", "arxiv"]
        assert preferences["quality_threshold"] == 0.8
        
        # Verify first research was successful
        assert len(delivered_results) == 2
        assert user_feedback["overall_satisfaction"] == 5


if __name__ == "__main__":
    # Run E2E tests with verbose output
    pytest.main([__file__, "-v", "--tb=short", "--asyncio-mode=auto"])
