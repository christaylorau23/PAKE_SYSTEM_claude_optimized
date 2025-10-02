#!/usr/bin/env python3
"""
PAKE System - Search History Service Tests
Comprehensive test suite for user search history management.
"""

import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from src.services.caching.redis_cache_service import RedisCacheService
from src.services.database.postgresql_service import PostgreSQLService
from src.services.user.search_history_service import (
    SearchAnalytics,
    SearchFilter,
    SearchHistoryEntry,
    SearchHistoryService,
    UserSearchPreferences,
    create_search_history_service,
)

# Import the service under test
sys.path.append(str(Path(__file__).parent.parent))


class TestSearchHistoryService:
    """Test suite for SearchHistoryService"""

    @pytest.fixture()
    async def mock_database_service(self):
        """Mock database service"""
        mock_db = Mock(spec=PostgreSQLService)
        mock_db.create_search_history = AsyncMock(return_value=str(uuid.uuid4()))
        mock_db.get_search_history = AsyncMock(return_value=[])
        mock_db.get_user_search_analytics = AsyncMock(
            return_value={
                "total_searches": 10,
                "unique_queries": 8,
                "avg_execution_time": 250.5,
                "cache_hit_rate": 0.75,
                "top_sources": [("web", 15), ("arxiv", 8)],
                "popular_queries": [("machine learning", 5), ("AI research", 3)],
                "search_frequency": {"daily": 2, "weekly": 10, "monthly": 30},
                "quality_distribution": {"high": 7, "medium": 2, "low": 1},
            },
        )
        mock_db.get_user_preferences = AsyncMock(return_value=None)
        mock_db.save_user_preferences = AsyncMock(return_value=True)
        mock_db.is_search_favorite = AsyncMock(return_value=False)
        mock_db.add_favorite_search = AsyncMock(return_value=True)
        mock_db.remove_favorite_search = AsyncMock(return_value=True)
        mock_db.get_search_tags = AsyncMock(return_value=[])
        mock_db.add_search_tags = AsyncMock(return_value=True)
        mock_db.delete_search_history = AsyncMock(return_value=True)
        mock_db.clear_user_search_history = AsyncMock(return_value=5)
        mock_db.get_search_by_id = AsyncMock(
            return_value={
                "id": "search-123",
                "user_id": "user-456",
                "query": "test query",
            },
        )
        mock_db.get_popular_queries = AsyncMock(
            return_value=[("machine learning", 10), ("AI research", 8)],
        )
        mock_db.search_history_fulltext = AsyncMock(return_value=[])
        return mock_db

    @pytest.fixture()
    async def mock_cache_service(self):
        """Mock cache service"""
        mock_cache = Mock(spec=RedisCacheService)
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock(return_value=True)
        mock_cache.delete = AsyncMock(return_value=True)
        mock_cache.delete_pattern = AsyncMock(return_value=True)
        return mock_cache

    @pytest.fixture()
    async def search_history_service(self, mock_database_service, mock_cache_service):
        """Create SearchHistoryService instance"""
        return SearchHistoryService(mock_database_service, mock_cache_service)

    @pytest.mark.asyncio()
    async def test_record_search_success(
        self,
        search_history_service,
        mock_database_service,
    ):
        """Test successful search recording"""
        user_id = "user-123"
        query = "machine learning algorithms"
        sources = ["web", "arxiv"]
        results_count = 15
        execution_time_ms = 250.5

        search_id = await search_history_service.record_search(
            user_id=user_id,
            query=query,
            sources=sources,
            results_count=results_count,
            execution_time_ms=execution_time_ms,
            cache_hit=False,
            quality_score=0.85,
        )

        assert search_id is not None
        mock_database_service.create_search_history.assert_called_once()

        # Verify call arguments
        call_args = mock_database_service.create_search_history.call_args
        assert call_args.kwargs["user_id"] == user_id
        assert call_args.kwargs["query"] == query
        assert call_args.kwargs["sources"] == sources
        assert call_args.kwargs["results_count"] == results_count
        assert call_args.kwargs["execution_time_ms"] == execution_time_ms

    @pytest.mark.asyncio()
    async def test_get_user_search_history_with_cache(
        self,
        search_history_service,
        mock_cache_service,
    ):
        """Test getting search history with cache hit"""
        user_id = "user-123"
        cached_data = [
            {
                "id": "search-1",
                "user_id": user_id,
                "query": "test query",
                "sources": ["web"],
                "results_count": 5,
                "execution_time_ms": 150.0,
                "cache_hit": False,
                "quality_score": 0.8,
                "query_metadata": {},
                "created_at": datetime.utcnow(),
                "is_favorite": False,
                "tags": [],
            },
        ]

        mock_cache_service.get.return_value = cached_data

        history = await search_history_service.get_user_search_history(
            user_id,
            limit=10,
        )

        assert len(history) == 1
        assert isinstance(history[0], SearchHistoryEntry)
        assert history[0].query == "test query"
        mock_cache_service.get.assert_called_once()

    @pytest.mark.asyncio()
    async def test_get_user_search_history_no_cache(
        self,
        search_history_service,
        mock_database_service,
        mock_cache_service,
    ):
        """Test getting search history without cache"""
        user_id = "user-123"
        mock_cache_service.get.return_value = None

        db_data = [
            {
                "id": "search-1",
                "user_id": user_id,
                "query": "test query",
                "sources": ["web"],
                "results_count": 5,
                "execution_time_ms": 150.0,
                "cache_hit": False,
                "quality_score": 0.8,
                "query_metadata": {},
                "created_at": datetime.utcnow(),
            },
        ]
        mock_database_service.get_search_history.return_value = db_data

        history = await search_history_service.get_user_search_history(
            user_id,
            limit=10,
        )

        assert len(history) == 1
        assert isinstance(history[0], SearchHistoryEntry)
        mock_database_service.get_search_history.assert_called_once()
        mock_cache_service.set.assert_called_once()  # Should cache the result

    @pytest.mark.asyncio()
    async def test_search_history_fulltext(
        self,
        search_history_service,
        mock_database_service,
    ):
        """Test full-text search in history"""
        user_id = "user-123"
        search_query = "machine learning"

        db_data = [
            {
                "id": "search-1",
                "user_id": user_id,
                "query": "machine learning basics",
                "sources": ["web"],
                "results_count": 8,
                "execution_time_ms": 180.0,
                "cache_hit": False,
                "quality_score": 0.9,
                "query_metadata": {},
                "created_at": datetime.utcnow(),
            },
        ]
        mock_database_service.search_history_fulltext.return_value = db_data

        results = await search_history_service.search_history(user_id, search_query)

        assert len(results) == 1
        assert results[0].query == "machine learning basics"
        mock_database_service.search_history_fulltext.assert_called_once()

    @pytest.mark.asyncio()
    async def test_toggle_favorite_search_add(
        self,
        search_history_service,
        mock_database_service,
    ):
        """Test adding search to favorites"""
        user_id = "user-123"
        search_id = "search-456"

        mock_database_service.is_search_favorite.return_value = False

        is_favorite = await search_history_service.toggle_favorite_search(
            user_id,
            search_id,
        )

        assert is_favorite is True
        mock_database_service.add_favorite_search.assert_called_once_with(
            user_id,
            search_id,
        )

    @pytest.mark.asyncio()
    async def test_toggle_favorite_search_remove(
        self,
        search_history_service,
        mock_database_service,
    ):
        """Test removing search from favorites"""
        user_id = "user-123"
        search_id = "search-456"

        mock_database_service.is_search_favorite.return_value = True

        is_favorite = await search_history_service.toggle_favorite_search(
            user_id,
            search_id,
        )

        assert is_favorite is False
        mock_database_service.remove_favorite_search.assert_called_once_with(
            user_id,
            search_id,
        )

    @pytest.mark.asyncio()
    async def test_add_search_tags_success(
        self,
        search_history_service,
        mock_database_service,
    ):
        """Test adding tags to search"""
        user_id = "user-123"
        search_id = "search-456"
        tags = ["machine-learning", "research"]

        success = await search_history_service.add_search_tags(user_id, search_id, tags)

        assert success is True
        mock_database_service.add_search_tags.assert_called_once_with(search_id, tags)

    @pytest.mark.asyncio()
    async def test_add_search_tags_unauthorized(
        self,
        search_history_service,
        mock_database_service,
    ):
        """Test adding tags to search owned by different user"""
        user_id = "user-123"
        search_id = "search-456"
        tags = ["test"]

        # Mock search owned by different user
        mock_database_service.get_search_by_id.return_value = {
            "id": search_id,
            "user_id": "different-user",
            "query": "test query",
        }

        success = await search_history_service.add_search_tags(user_id, search_id, tags)

        assert success is False
        mock_database_service.add_search_tags.assert_not_called()

    @pytest.mark.asyncio()
    async def test_delete_search_success(
        self,
        search_history_service,
        mock_database_service,
    ):
        """Test successful search deletion"""
        user_id = "user-123"
        search_id = "search-456"

        success = await search_history_service.delete_search(user_id, search_id)

        assert success is True
        mock_database_service.delete_search_history.assert_called_once_with(search_id)

    @pytest.mark.asyncio()
    async def test_clear_user_history(
        self,
        search_history_service,
        mock_database_service,
    ):
        """Test clearing user search history"""
        user_id = "user-123"
        before_date = datetime.utcnow() - timedelta(days=30)

        deleted_count = await search_history_service.clear_user_history(
            user_id,
            before_date,
        )

        assert deleted_count == 5  # Mock returns 5
        mock_database_service.clear_user_search_history.assert_called_once_with(
            user_id,
            before_date,
        )

    @pytest.mark.asyncio()
    async def test_get_user_analytics_with_cache(
        self,
        search_history_service,
        mock_cache_service,
    ):
        """Test getting analytics with cache hit"""
        user_id = "user-123"
        cached_analytics = {
            "total_searches": 20,
            "unique_queries": 15,
            "avg_execution_time": 200.0,
            "cache_hit_rate": 0.8,
            "top_sources": [("web", 12), ("arxiv", 8)],
            "popular_queries": [("AI", 5)],
            "search_frequency": {"daily": 3},
            "quality_distribution": {"high": 10},
        }

        mock_cache_service.get.return_value = cached_analytics

        analytics = await search_history_service.get_user_analytics(user_id)

        assert isinstance(analytics, SearchAnalytics)
        assert analytics.total_searches == 20
        mock_cache_service.get.assert_called_once()

    @pytest.mark.asyncio()
    async def test_get_popular_queries(
        self,
        search_history_service,
        mock_database_service,
        mock_cache_service,
    ):
        """Test getting popular queries"""
        mock_cache_service.get.return_value = None

        popular_queries = await search_history_service.get_popular_queries(
            limit=5,
            days=7,
        )

        assert len(popular_queries) == 2
        assert popular_queries[0] == ("machine learning", 10)
        mock_database_service.get_popular_queries.assert_called_once()

    @pytest.mark.asyncio()
    async def test_get_user_preferences_default(
        self,
        search_history_service,
        mock_database_service,
    ):
        """Test getting user preferences with defaults"""
        user_id = "user-123"

        # Mock no existing preferences
        mock_database_service.get_user_preferences.return_value = None

        preferences = await search_history_service.get_user_preferences(user_id)

        assert isinstance(preferences, UserSearchPreferences)
        assert preferences.user_id == user_id
        assert preferences.default_sources == ["web", "arxiv", "pubmed"]
        assert preferences.auto_save_searches is True
        mock_database_service.save_user_preferences.assert_called_once()

    @pytest.mark.asyncio()
    async def test_update_user_preferences(
        self,
        search_history_service,
        mock_database_service,
        mock_cache_service,
    ):
        """Test updating user preferences"""
        user_id = "user-123"
        updates = {"default_sources": ["web", "arxiv"], "auto_save_searches": False}

        # Mock existing preferences
        existing_prefs = {
            "user_id": user_id,
            "default_sources": ["web", "arxiv", "pubmed"],
            "auto_save_searches": True,
            "search_history_retention_days": 365,
            "preferred_result_format": "detailed",
            "notification_settings": {},
            "privacy_settings": {},
            "updated_at": datetime.utcnow(),
        }
        mock_database_service.get_user_preferences.return_value = existing_prefs

        success = await search_history_service.update_user_preferences(user_id, updates)

        assert success is True
        mock_database_service.save_user_preferences.assert_called()
        mock_cache_service.delete.assert_called_once()  # Should invalidate cache

    @pytest.mark.asyncio()
    async def test_export_user_data(
        self,
        search_history_service,
        mock_database_service,
    ):
        """Test exporting user data"""
        user_id = "user-123"

        # Mock methods used in export
        search_history_service.get_user_search_history = AsyncMock(return_value=[])
        search_history_service.get_user_preferences = AsyncMock(
            return_value=UserSearchPreferences(
                user_id=user_id,
                default_sources=["web"],
                auto_save_searches=True,
                search_history_retention_days=365,
                preferred_result_format="detailed",
                notification_settings={},
                privacy_settings={},
                updated_at=datetime.utcnow(),
            ),
        )
        search_history_service.get_user_analytics = AsyncMock(
            return_value=SearchAnalytics(
                total_searches=10,
                unique_queries=8,
                avg_execution_time=200.0,
                cache_hit_rate=0.7,
                top_sources=[],
                popular_queries=[],
                search_frequency={},
                quality_distribution={},
            ),
        )

        export_data = await search_history_service.export_user_data(user_id)

        assert "export_date" in export_data
        assert export_data["user_id"] == user_id
        assert "search_history" in export_data
        assert "preferences" in export_data
        assert "analytics" in export_data
        assert "metadata" in export_data

    @pytest.mark.asyncio()
    async def test_filter_by_quality(
        self,
        search_history_service,
        mock_database_service,
        mock_cache_service,
    ):
        """Test filtering search history by quality"""
        user_id = "user-123"
        mock_cache_service.get.return_value = None

        db_data = [
            {
                "id": "search-1",
                "user_id": user_id,
                "query": "high quality search",
                "sources": ["web"],
                "results_count": 10,
                "execution_time_ms": 150.0,
                "cache_hit": False,
                "quality_score": 0.9,
                "query_metadata": {},
                "created_at": datetime.utcnow(),
            },
        ]
        mock_database_service.get_search_history.return_value = db_data

        await search_history_service.get_user_search_history(
            user_id,
            filter_type=SearchFilter.BY_QUALITY,
        )

        # Verify the filter was applied in database call
        call_args = mock_database_service.get_search_history.call_args
        assert "quality_score__gte" in call_args.kwargs["filters"]
        assert call_args.kwargs["order_by"] == ("quality_score DESC, created_at DESC")

    @pytest.mark.asyncio()
    async def test_error_handling_database_failure(
        self,
        search_history_service,
        mock_database_service,
    ):
        """Test error handling when database fails"""
        user_id = "user-123"

        # Mock database failure
        mock_database_service.create_search_history.side_effect = Exception(
            "Database error",
        )

        with pytest.raises(Exception) as exc_info:
            await search_history_service.record_search(
                user_id=user_id,
                query="test",
                sources=["web"],
                results_count=1,
                execution_time_ms=100.0,
            )

        assert "Database error" in str(exc_info.value)

    @pytest.mark.asyncio()
    async def test_cache_invalidation(self, search_history_service, mock_cache_service):
        """Test cache invalidation patterns"""
        user_id = "user-123"

        await search_history_service._invalidate_user_caches(user_id)

        # Should call delete_pattern for all user-related cache keys
        assert mock_cache_service.delete_pattern.call_count == 3

        call_args_list = [
            call.args[0] for call in mock_cache_service.delete_pattern.call_args_list
        ]
        assert f"search_history:user:{user_id}:*" in call_args_list
        assert f"search_history:analytics:user:{user_id}:*" in call_args_list
        assert f"search_history:prefs:{user_id}" in call_args_list


@pytest.mark.asyncio()
async def test_create_search_history_service():
    """Test factory function"""
    mock_db = Mock(spec=PostgreSQLService)
    mock_cache = Mock(spec=RedisCacheService)

    service = await create_search_history_service(mock_db, mock_cache)

    assert isinstance(service, SearchHistoryService)
    assert service.database_service == mock_db
    assert service.cache_service == mock_cache


if __name__ == "__main__":
    pytest.main([__file__])
