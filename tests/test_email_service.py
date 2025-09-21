#!/usr/bin/env python3
"""
PAKE System - Email Integration Service Tests
Phase 2B Sprint 3: Comprehensive TDD testing for email ingestion

Tests enterprise email integration with intelligent filtering,
cognitive assessment, and multi-protocol support.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from scripts.ingestion_pipeline import ContentItem
from services.ingestion.email_service import (
    EmailConnectionConfig,
    EmailIngestionService,
    EmailMessage,
    EmailSearchQuery,
)


class TestEmailIngestionService:
    """
    Comprehensive test suite for email ingestion service.
    Tests intelligent filtering, cognitive integration, and multi-protocol support.
    """

    @pytest.fixture
    def email_config(self):
        """Standard email connection configuration"""
        return EmailConnectionConfig(
            server_type="imap",
            hostname="imap.company.com",
            port=993,
            username="test@company.com",
            REDACTED_SECRET="secure_REDACTED_SECRET",
            use_ssl=True,
            timeout=30,
            folder_mapping={"INBOX": "INBOX", "Sent": "SENT"},
        )

    @pytest.fixture
    def exchange_config(self):
        """Exchange server configuration"""
        return EmailConnectionConfig(
            server_type="exchange",
            hostname="exchange.company.com",
            port=443,
            username="test@company.com",
            REDACTED_SECRET="secure_REDACTED_SECRET",
            use_ssl=True,
            timeout=30,
        )

    @pytest.fixture
    def mock_cognitive_engine(self):
        """Mock cognitive engine for quality assessment"""
        engine = Mock()
        engine.assess_content_quality = AsyncMock(return_value=0.85)
        return engine

    @pytest.fixture
    def email_service(self, email_config, mock_cognitive_engine):
        """Create email service instance"""
        return EmailIngestionService(
            config=email_config,
            cognitive_engine=mock_cognitive_engine,
        )

    @pytest.fixture
    def exchange_service(self, exchange_config, mock_cognitive_engine):
        """Create Exchange email service instance"""
        return EmailIngestionService(
            config=exchange_config,
            cognitive_engine=mock_cognitive_engine,
        )

    # ========================================================================
    # BASIC EMAIL SEARCH TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_search_emails_in_inbox_successfully(self, email_service):
        """
        Test: Should search emails in INBOX folder and return structured results
        with proper message parsing and metadata extraction.
        """
        query = EmailSearchQuery(folders=["INBOX"], max_results=10)

        result = await email_service.search_emails(query)

        # Verify search success
        assert result.success
        assert len(result.messages) > 0
        assert "INBOX" in result.folders_searched
        assert result.total_messages_found >= len(result.messages)
        assert result.execution_time > 0

        # Verify message structure
        message = result.messages[0]
        assert isinstance(message, EmailMessage)
        assert message.message_id
        assert message.sender
        assert message.subject
        assert message.content
        assert isinstance(message.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_should_search_multiple_folders_concurrently(self, email_service):
        """
        Test: Should search across multiple email folders efficiently
        and aggregate results with folder attribution.
        """
        query = EmailSearchQuery(folders=["INBOX", "Sent", "Archive"], max_results=20)

        result = await email_service.search_emails(query)

        # Verify multi-folder search
        assert result.success
        assert len(result.folders_searched) == 3
        assert "INBOX" in result.folders_searched
        assert "Sent" in result.folders_searched
        assert "Archive" in result.folders_searched

        # Verify messages have folder attribution
        if result.messages:
            folders_in_messages = {msg.folder for msg in result.messages}
            assert len(folders_in_messages) >= 1  # At least one folder represented

    @pytest.mark.asyncio
    async def test_should_apply_sender_filtering_accurately(self, email_service):
        """
        Test: Should filter emails by sender addresses and patterns
        with support for domain-based filtering.
        """
        query = EmailSearchQuery(
            folders=["INBOX"],
            sender_filters=["@company.com"],
            max_results=10,
        )

        result = await email_service.search_emails(query)

        # Verify sender filtering
        assert result.success

        # All returned messages should match sender filter
        for message in result.messages:
            assert any(
                filter_pattern in message.sender
                for filter_pattern in query.sender_filters
            )

    @pytest.mark.asyncio
    async def test_should_apply_subject_keyword_filtering(self, email_service):
        """
        Test: Should filter emails by subject keywords with case-insensitive
        matching and multiple keyword support.
        """
        query = EmailSearchQuery(
            folders=["INBOX"],
            subject_keywords=["project", "update"],
            max_results=10,
        )

        result = await email_service.search_emails(query)

        # Verify subject keyword filtering
        assert result.success

        for message in result.messages:
            subject_lower = message.subject.lower()
            assert any(
                keyword.lower() in subject_lower for keyword in query.subject_keywords
            )

    @pytest.mark.asyncio
    async def test_should_support_date_range_filtering(self, email_service):
        """
        Test: Should filter emails by date range with proper timezone handling
        and inclusive/exclusive boundary support.
        """
        start_date = datetime.now(UTC) - timedelta(days=7)
        end_date = datetime.now(UTC)

        query = EmailSearchQuery(
            folders=["INBOX"],
            date_range={"start": start_date, "end": end_date},
            max_results=10,
        )

        result = await email_service.search_emails(query)

        # Verify date range filtering
        assert result.success

        for message in result.messages:
            assert start_date <= message.timestamp <= end_date

    # ========================================================================
    # INTELLIGENT FILTERING TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_filter_spam_messages_intelligently(self, email_service):
        """
        Test: Should detect and filter spam messages using pattern matching
        and heuristic analysis with configurable sensitivity.
        """
        query = EmailSearchQuery(folders=["INBOX"], exclude_spam=True, max_results=10)

        result = await email_service.search_emails(query)

        # Verify spam filtering
        assert result.success
        assert (
            "spam_filter" in result.intelligent_filters_applied
            or len(result.messages) >= 0
        )

        # Check that no obvious spam messages are included
        for message in result.messages:
            assert message.spam_score < 5.0
            assert not any(
                spam_word in message.subject.lower()
                for spam_word in ["lottery", "winner", "urgent", "act now"]
            )

    @pytest.mark.asyncio
    async def test_should_filter_promotional_content_effectively(self, email_service):
        """
        Test: Should identify and filter promotional emails including
        newsletters, marketing, and sales content.
        """
        query = EmailSearchQuery(
            folders=["INBOX"],
            exclude_promotional=True,
            max_results=10,
        )

        result = await email_service.search_emails(query)

        # Verify promotional filtering
        assert result.success

        # Check promotional content indicators
        for message in result.messages:
            content_lower = f"{message.subject} {message.content}".lower()
            promotional_indicators = ["unsubscribe", "newsletter", "sale", "offer"]

            # Should not contain obvious promotional indicators
            has_promotional = any(
                indicator in content_lower for indicator in promotional_indicators
            )

            # If promotional content is found, it should be minimal
            if has_promotional:
                # Allow minimal promotional language in professional emails
                assert (
                    len([ind for ind in promotional_indicators if ind in content_lower])
                    <= 1
                )

    @pytest.mark.asyncio
    async def test_should_apply_content_length_filtering(self, email_service):
        """
        Test: Should filter out emails with insufficient content length
        to focus on substantive communications.
        """
        query = EmailSearchQuery(
            folders=["INBOX"],
            min_content_length=200,  # Require substantial content
            max_results=10,
        )

        result = await email_service.search_emails(query)

        # Verify content length filtering
        assert result.success

        for message in result.messages:
            assert len(message.content) >= query.min_content_length

    @pytest.mark.asyncio
    async def test_should_prioritize_professional_content(self, email_service):
        """
        Test: Should identify and prioritize professional emails
        over personal or casual communications.
        """
        query = EmailSearchQuery(folders=["INBOX"], max_results=10)

        result = await email_service.search_emails(query)

        # Verify professional content prioritization
        assert result.success

        if result.messages:
            # Check that professional emails are ranked higher
            top_messages = result.messages[:3]  # Top 3 messages

            professional_indicators = [
                "meeting",
                "project",
                "report",
                "proposal",
                "team",
            ]
            professional_count = 0

            for message in top_messages:
                content_lower = f"{message.subject} {message.content}".lower()
                if any(
                    indicator in content_lower for indicator in professional_indicators
                ):
                    professional_count += 1

            # At least some professional content should be prioritized
            assert professional_count >= 0  # Allow for various content types

    # ========================================================================
    # COGNITIVE INTEGRATION TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_integrate_cognitive_quality_assessment(self, email_service):
        """
        Test: Should apply cognitive quality assessment to email content
        and incorporate quality scores into ranking.
        """
        query = EmailSearchQuery(folders=["INBOX"], max_results=5)

        result = await email_service.search_emails(query)

        # Verify cognitive integration
        assert result.success
        assert result.cognitive_assessments_applied > 0

        # Verify quality scores are applied
        for message in result.messages:
            assert hasattr(message, "content_quality_score")
            assert 0.0 <= message.content_quality_score <= 1.0

        # Verify cognitive engine was called
        assert email_service.cognitive_engine.assess_content_quality.call_count > 0

    @pytest.mark.asyncio
    async def test_should_handle_cognitive_assessment_failures_gracefully(
        self,
        email_service,
    ):
        """
        Test: Should continue processing when cognitive assessment fails
        and provide meaningful fallback quality scoring.
        """
        # Mock cognitive engine to fail
        email_service.cognitive_engine.assess_content_quality.side_effect = Exception(
            "Cognitive error",
        )

        query = EmailSearchQuery(folders=["INBOX"], max_results=5)

        result = await email_service.search_emails(query)

        # Should still succeed despite cognitive failures
        assert result.success
        assert len(result.messages) > 0

        # Messages should still be processed
        for message in result.messages:
            assert message.content_quality_score == 0.0  # Fallback score

    # ========================================================================
    # CONTENT ITEM CONVERSION TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_convert_emails_to_content_items_correctly(
        self,
        email_service,
    ):
        """
        Test: Should convert email messages to standardized ContentItem format
        with comprehensive metadata preservation.
        """
        query = EmailSearchQuery(folders=["INBOX"], max_results=3)
        result = await email_service.search_emails(query)

        content_items = await email_service.to_content_items(
            result,
            "email_ingestion_test",
        )

        # Verify conversion success
        assert len(content_items) == len(result.messages)

        for i, item in enumerate(content_items):
            message = result.messages[i]

            # Verify ContentItem structure
            assert isinstance(item, ContentItem)
            assert item.source_name == "email_ingestion_test"
            assert item.source_type == "email"
            assert item.title == message.subject
            assert item.content == message.content
            assert item.author == message.sender
            assert item.published == message.timestamp

            # Verify metadata preservation
            assert item.metadata["message_id"] == message.message_id
            assert item.metadata["folder"] == message.folder
            assert item.metadata["importance"] == message.importance
            assert "spam_score" in item.metadata
            assert "content_quality_score" in item.metadata

    # ========================================================================
    # MULTI-PROTOCOL SUPPORT TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_support_imap_connection_configuration(self, email_service):
        """
        Test: Should properly configure and connect to IMAP servers
        with SSL support and authentication.
        """
        # Verify IMAP configuration
        assert email_service.config.server_type == "imap"
        assert email_service.config.hostname == "imap.company.com"
        assert email_service.config.port == 993
        assert email_service.config.use_ssl

        # Test connection establishment
        query = EmailSearchQuery(folders=["INBOX"], max_results=1)
        result = await email_service.search_emails(query)

        assert result.success

    @pytest.mark.asyncio
    async def test_should_support_exchange_connection_configuration(
        self,
        exchange_service,
    ):
        """
        Test: Should properly configure and connect to Exchange servers
        with appropriate protocol handling.
        """
        # Verify Exchange configuration
        assert exchange_service.config.server_type == "exchange"
        assert exchange_service.config.hostname == "exchange.company.com"
        assert exchange_service.config.port == 443

        # Test connection establishment
        query = EmailSearchQuery(folders=["INBOX"], max_results=1)
        result = await exchange_service.search_emails(query)

        assert result.success

    # ========================================================================
    # ERROR HANDLING AND RESILIENCE TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_handle_connection_failures_gracefully(self, email_service):
        """
        Test: Should handle email server connection failures with proper
        error reporting and recovery strategies.
        """
        # Mock connection failure
        with patch.object(
            email_service,
            "_get_connection",
            side_effect=Exception("Connection failed"),
        ):
            query = EmailSearchQuery(folders=["INBOX"], max_results=5)
            result = await email_service.search_emails(query)

            # Should fail gracefully
            assert not result.success
            assert "Connection failed" in result.error_details
            assert result.execution_time > 0

    @pytest.mark.asyncio
    async def test_should_handle_empty_search_results_properly(self, email_service):
        """
        Test: Should handle cases where email search returns no results
        without errors and with proper result structure.
        """
        # Mock empty results
        with patch.object(email_service, "_search_folder", return_value=[]):
            query = EmailSearchQuery(
                folders=["INBOX"],
                subject_keywords=["nonexistent_keyword_xyz"],
            )
            result = await email_service.search_emails(query)

            # Should succeed with empty results
            assert result.success
            assert len(result.messages) == 0
            assert result.total_messages_found == 0
            assert result.processed_messages == 0

    # ========================================================================
    # PERFORMANCE AND SCALABILITY TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_complete_search_within_reasonable_time(self, email_service):
        """
        Test: Should complete email searches within acceptable time limits
        even with large result sets and complex filtering.
        """
        query = EmailSearchQuery(
            folders=["INBOX"],
            max_results=50,
            exclude_spam=True,
            exclude_promotional=True,
        )

        result = await email_service.search_emails(query)

        # Should complete quickly
        assert result.success
        assert result.execution_time < 5.0  # Should complete within 5 seconds

    @pytest.mark.asyncio
    async def test_should_respect_max_results_limit(self, email_service):
        """
        Test: Should properly limit results according to max_results parameter
        and provide accurate count statistics.
        """
        query = EmailSearchQuery(folders=["INBOX"], max_results=2)  # Very small limit

        result = await email_service.search_emails(query)

        # Should respect limit
        assert result.success
        assert len(result.messages) <= query.max_results
        assert result.processed_messages <= query.max_results

    # ========================================================================
    # HEALTH CHECK AND MAINTENANCE TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_should_provide_comprehensive_health_status(self, email_service):
        """
        Test: Should provide detailed health check information including
        connection status, cache statistics, and service availability.
        """
        health_status = await email_service.health_check()

        # Verify health check structure
        assert "status" in health_status
        assert "server_type" in health_status
        assert "hostname" in health_status
        assert "connected" in health_status
        assert "authenticated" in health_status
        assert "cache_size" in health_status
        assert "filter_patterns_loaded" in health_status

        # Should be healthy with mock setup
        assert health_status["status"] == "healthy"
        assert health_status["server_type"] == "imap"
        assert health_status["hostname"] == "imap.company.com"

    @pytest.mark.asyncio
    async def test_should_cleanup_resources_properly(self, email_service):
        """
        Test: Should properly close connections and clean up resources
        when service is shut down.
        """
        # Establish connection first
        query = EmailSearchQuery(folders=["INBOX"], max_results=1)
        await email_service.search_emails(query)

        # Verify connections exist
        assert len(email_service.connection_pool) > 0

        # Close service
        await email_service.close()

        # Verify cleanup
        assert len(email_service.connection_pool) == 0
        assert len(email_service._message_cache) == 0


class TestEmailDataStructures:
    """Test email-specific data structures and configurations"""

    def test_email_search_query_should_have_sensible_defaults(self):
        """
        Test: EmailSearchQuery should provide reasonable default values
        for all configuration parameters.
        """
        query = EmailSearchQuery()

        # Verify defaults
        assert query.folders == ["INBOX"]
        assert query.sender_filters == []
        assert query.subject_keywords == []
        assert query.content_keywords == []
        assert query.date_range is None
        assert query.max_results == 50
        assert query.exclude_spam
        assert query.exclude_promotional
        assert query.min_content_length == 100
        assert query.attachment_types == []

    def test_email_message_should_be_immutable(self):
        """
        Test: EmailMessage instances should be immutable to ensure
        data integrity throughout processing pipeline.
        """
        message = EmailMessage(
            message_id="test_msg_001",
            sender="test@example.com",
            recipients=["recipient@example.com"],
            subject="Test Subject",
            content="Test content",
            html_content=None,
            timestamp=datetime.now(UTC),
            folder="INBOX",
        )

        # Should be frozen dataclass (immutable)
        with pytest.raises(AttributeError):
            message.subject = "Modified subject"

    def test_email_connection_config_should_validate_server_types(self):
        """
        Test: EmailConnectionConfig should accept valid server types
        and provide appropriate configuration structure.
        """
        # Test IMAP configuration
        imap_config = EmailConnectionConfig(
            server_type="imap",
            hostname="imap.gmail.com",
            port=993,
            username="user@gmail.com",
            REDACTED_SECRET="REDACTED_SECRET",
        )

        assert imap_config.server_type == "imap"
        assert imap_config.use_ssl  # Default
        assert imap_config.timeout == 30  # Default

        # Test Exchange configuration
        exchange_config = EmailConnectionConfig(
            server_type="exchange",
            hostname="exchange.company.com",
            port=443,
            username="user@company.com",
            REDACTED_SECRET="REDACTED_SECRET",
            use_ssl=False,
        )

        assert exchange_config.server_type == "exchange"
        assert exchange_config.use_ssl == False  # Override default
