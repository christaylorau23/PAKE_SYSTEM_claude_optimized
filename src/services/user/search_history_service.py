#!/usr/bin/env python3
"""PAKE System - User Search History Management Service
Comprehensive search history tracking with analytics and user preferences.
"""

import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from ..caching.redis_cache_service import RedisCacheService
from ..database.postgresql_service import PostgreSQLService

logger = logging.getLogger(__name__)


class SearchFilter(Enum):
    """Search filter options"""

    RECENT = "recent"
    POPULAR = "popular"
    FAVORITES = "favorites"
    BY_SOURCE = "by_source"
    BY_DATE_RANGE = "by_date_range"
    BY_QUALITY = "by_quality"


@dataclass
class SearchHistoryEntry:
    """Individual search history entry"""

    id: str
    user_id: str | None
    query: str
    sources: list[str]
    results_count: int
    execution_time_ms: float
    cache_hit: bool
    quality_score: float | None
    query_metadata: dict[str, Any] | None
    created_at: datetime
    is_favorite: bool = False
    tags: list[str] | None = None


@dataclass
class SearchAnalytics:
    """Search analytics data"""

    total_searches: int
    unique_queries: int
    avg_execution_time: float
    cache_hit_rate: float
    top_sources: list[tuple[str, int]]
    popular_queries: list[tuple[str, int]]
    search_frequency: dict[str, int]  # searches per day/week/month
    quality_distribution: dict[str, int]


@dataclass
class UserSearchPreferences:
    """User search preferences and settings"""

    user_id: str
    default_sources: list[str]
    auto_save_searches: bool
    search_history_retention_days: int
    preferred_result_format: str
    notification_settings: dict[str, bool]
    privacy_settings: dict[str, bool]
    updated_at: datetime


class SearchHistoryService:
    """Comprehensive search history management service.

    Features:
    - Real-time search tracking
    - Advanced filtering and search
    - User preferences management
    - Analytics and insights
    - Privacy controls
    - Export/import functionality
    """

    def __init__(
        self,
        database_service: PostgreSQLService,
        cache_service: RedisCacheService | None = None,
    ):
        self.database_service = database_service
        self.cache_service = cache_service
        self.logger = logger

        # Cache keys
        self.CACHE_PREFIX = "search_history"
        self.USER_PREFS_CACHE_TTL = 3600  # 1 hour
        self.ANALYTICS_CACHE_TTL = 1800  # 30 minutes

        logger.info("✅ Search History Service initialized")

    # Search History Management

    async def record_search(
        self,
        user_id: str | None,
        query: str,
        sources: list[str],
        results_count: int,
        execution_time_ms: float,
        cache_hit: bool = False,
        quality_score: float | None = None,
        query_metadata: dict[str, Any] | None = None,
    ) -> str:
        """Record a new search in history"""
        try:
            search_id = str(uuid.uuid4())

            # Store in database
            await self.database_service.create_search_history(
                user_id=user_id,
                query=query,
                sources=sources,
                results_count=results_count,
                execution_time_ms=execution_time_ms,
                cache_hit=cache_hit,
                quality_score=quality_score,
                query_metadata=query_metadata or {},
            )

            # Invalidate relevant caches
            if self.cache_service and user_id:
                await self._invalidate_user_caches(user_id)

            logger.info(
                f"📝 Recorded search: {query[:50]}... for user {user_id or 'anonymous'}",
            )
            return search_id

        except Exception as e:
            logger.error(f"Failed to record search: {e}")
            raise

    async def get_user_search_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        filter_type: SearchFilter | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        sources: list[str] | None = None,
    ) -> list[SearchHistoryEntry]:
        """Get user's search history with advanced filtering"""
        try:
            # Check cache first
            cache_key = f"{self.CACHE_PREFIX}:user:{user_id}:history:{limit}:{offset}"
            if self.cache_service:
                cached_result = await self.cache_service.get(cache_key)
                if cached_result:
                    return [SearchHistoryEntry(**entry) for entry in cached_result]

            # Build query filters
            filters: dict[str, Any] = {"user_id": user_id}

            if start_date is not None:
                filters["start_date"] = start_date.isoformat()
            if end_date is not None:
                filters["end_date"] = end_date.isoformat()
            if sources is not None:
                filters["sources"] = sources

            # Apply special filters
            order_by = "created_at DESC"
            if filter_type == SearchFilter.POPULAR:
                order_by = "results_count DESC, created_at DESC"
            elif filter_type == SearchFilter.BY_QUALITY:
                order_by = "quality_score DESC, created_at DESC"
                filters["quality_score__gte"] = "0.5"

            # Get from database
            search_records = await self.database_service.get_search_history(
                filters=filters,
                limit=limit,
                offset=offset,
                order_by=order_by,
            )

            # Convert to SearchHistoryEntry objects
            history_entries = []
            for record in search_records:
                entry = SearchHistoryEntry(
                    id=record["id"],
                    user_id=record["user_id"],
                    query=record["query"],
                    sources=record["sources"],
                    results_count=record["results_count"],
                    execution_time_ms=record["execution_time_ms"],
                    cache_hit=record["cache_hit"],
                    quality_score=record["quality_score"],
                    query_metadata=record["query_metadata"],
                    created_at=record["created_at"],
                    is_favorite=await self._is_search_favorite(user_id, record["id"]),
                    tags=await self._get_search_tags(record["id"]),
                )
                history_entries.append(entry)

            # Cache the results
            if self.cache_service:
                cache_data = [asdict(entry) for entry in history_entries]
                await self.cache_service.set(
                    cache_key,
                    cache_data,
                    ttl=300,  # 5 minutes
                )

            return history_entries

        except Exception as e:
            logger.error(f"Failed to get search history: {e}")
            raise

    async def search_history(
        self,
        user_id: str,
        search_query: str,
        limit: int = 20,
    ) -> list[SearchHistoryEntry]:
        """Search through user's search history"""
        try:
            # Use full-text search on query and metadata
            search_filters = {"user_id": user_id, "query_search": search_query}

            search_records = await self.database_service.search_history_fulltext(
                filters=search_filters,
                limit=limit,
            )

            # Convert to SearchHistoryEntry objects
            history_entries = []
            for record in search_records:
                entry = SearchHistoryEntry(
                    id=record["id"],
                    user_id=record["user_id"],
                    query=record["query"],
                    sources=record["sources"],
                    results_count=record["results_count"],
                    execution_time_ms=record["execution_time_ms"],
                    cache_hit=record["cache_hit"],
                    quality_score=record["quality_score"],
                    query_metadata=record["query_metadata"],
                    created_at=record["created_at"],
                    is_favorite=await self._is_search_favorite(user_id, record["id"]),
                    tags=await self._get_search_tags(record["id"]),
                )
                history_entries.append(entry)

            return history_entries

        except Exception as e:
            logger.error(f"Failed to search history: {e}")
            raise

    async def toggle_favorite_search(self, user_id: str, search_id: str) -> bool:
        """Toggle favorite status of a search"""
        try:
            is_favorite = await self._is_search_favorite(user_id, search_id)

            if is_favorite:
                await self.database_service.remove_favorite_search(user_id, search_id)
                new_status = False
            else:
                await self.database_service.add_favorite_search(user_id, search_id)
                new_status = True

            # Invalidate caches
            if self.cache_service:
                await self._invalidate_user_caches(user_id)

            logger.info(
                f"💫 {'Added to' if new_status else 'Removed from'} favorites: {
                    search_id
                }",
            )
            return new_status

        except Exception as e:
            logger.error(f"Failed to toggle favorite: {e}")
            raise

    async def add_search_tags(
        self,
        user_id: str,
        search_id: str,
        tags: list[str],
    ) -> bool:
        """Add tags to a search entry"""
        try:
            # Verify user owns the search
            search = await self.database_service.get_search_by_id(search_id)
            if not search or search["user_id"] != user_id:
                return False

            await self.database_service.add_search_tags(search_id, tags)

            # Invalidate caches
            if self.cache_service:
                await self._invalidate_user_caches(user_id)

            logger.info(f"🏷️ Added tags {tags} to search {search_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add tags: {e}")
            raise

    async def delete_search(self, user_id: str, search_id: str) -> bool:
        """Delete a search from history"""
        try:
            # Verify user owns the search
            search = await self.database_service.get_search_by_id(search_id)
            if not search or search["user_id"] != user_id:
                return False

            await self.database_service.delete_search_history(search_id)

            # Invalidate caches
            if self.cache_service:
                await self._invalidate_user_caches(user_id)

            logger.info(f"🗑️ Deleted search {search_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete search: {e}")
            raise

    async def clear_user_history(
        self,
        user_id: str,
        before_date: datetime | None = None,
    ) -> int:
        """Clear user's search history"""
        try:
            deleted_count = await self.database_service.clear_user_search_history(
                user_id,
                before_date,
            )

            # Invalidate caches
            if self.cache_service:
                await self._invalidate_user_caches(user_id)

            logger.info(f"🧹 Cleared {deleted_count} search records for user {user_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
            raise

    # Analytics and Insights

    async def get_user_analytics(self, user_id: str, days: int = 30) -> SearchAnalytics:
        """Get comprehensive search analytics for user"""
        try:
            # Check cache first
            cache_key = f"{self.CACHE_PREFIX}:analytics:user:{user_id}:{days}"
            if self.cache_service:
                cached_result = await self.cache_service.get(cache_key)
                if cached_result:
                    return SearchAnalytics(**cached_result)

            # Calculate date range
            start_date = datetime.utcnow() - timedelta(days=days)

            # Get analytics data from database
            analytics_data = await self.database_service.get_user_search_analytics(
                user_id,
                start_date,
            )

            analytics = SearchAnalytics(
                total_searches=analytics_data["total_searches"],
                unique_queries=analytics_data["unique_queries"],
                avg_execution_time=analytics_data["avg_execution_time"],
                cache_hit_rate=analytics_data["cache_hit_rate"],
                top_sources=analytics_data["top_sources"],
                popular_queries=analytics_data["popular_queries"],
                search_frequency=analytics_data["search_frequency"],
                quality_distribution=analytics_data["quality_distribution"],
            )

            # Cache the results
            if self.cache_service:
                await self.cache_service.set(
                    cache_key,
                    asdict(analytics),
                    ttl=self.ANALYTICS_CACHE_TTL,
                )

            return analytics

        except Exception as e:
            logger.error(f"Failed to get analytics: {e}")
            raise

    async def get_popular_queries(
        self,
        limit: int = 10,
        days: int = 7,
    ) -> list[tuple[str, int]]:
        """Get most popular queries across all users"""
        try:
            # Check cache first
            cache_key = f"{self.CACHE_PREFIX}:popular:{limit}:{days}"
            if self.cache_service:
                cached_result = await self.cache_service.get(cache_key)
                if cached_result:
                    return cached_result

            start_date = datetime.utcnow() - timedelta(days=days)
            popular_queries = await self.database_service.get_popular_queries(
                start_date,
                limit,
            )

            # Cache the results
            if self.cache_service:
                await self.cache_service.set(
                    cache_key,
                    popular_queries,
                    ttl=self.ANALYTICS_CACHE_TTL,
                )

            return popular_queries

        except Exception as e:
            logger.error(f"Failed to get popular queries: {e}")
            raise

    # User Preferences Management

    async def get_user_preferences(self, user_id: str) -> UserSearchPreferences:
        """Get user's search preferences"""
        try:
            # Check cache first
            cache_key = f"{self.CACHE_PREFIX}:prefs:{user_id}"
            if self.cache_service:
                cached_result = await self.cache_service.get(cache_key)
                if cached_result:
                    return UserSearchPreferences(**cached_result)

            # Get from database or create defaults
            prefs_data = await self.database_service.get_user_preferences(user_id)

            if not prefs_data:
                # Create default preferences
                prefs = UserSearchPreferences(
                    user_id=user_id,
                    default_sources=["web", "arxiv", "pubmed"],
                    auto_save_searches=True,
                    search_history_retention_days=365,
                    preferred_result_format="detailed",
                    notification_settings={
                        "email_digest": False,
                        "search_alerts": True,
                        "weekly_summary": False,
                    },
                    privacy_settings={
                        "anonymous_analytics": False,
                        "share_popular_searches": True,
                        "retention_opt_out": False,
                    },
                    updated_at=datetime.utcnow(),
                )

                # Save defaults to database
                await self.database_service.save_user_preferences(
                    user_id,
                    asdict(prefs),
                )
            else:
                prefs = UserSearchPreferences(**prefs_data)

            # Cache the preferences
            if self.cache_service:
                await self.cache_service.set(
                    cache_key,
                    asdict(prefs),
                    ttl=self.USER_PREFS_CACHE_TTL,
                )

            return prefs

        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}")
            raise

    async def update_user_preferences(
        self,
        user_id: str,
        preferences: dict[str, Any],
    ) -> bool:
        """Update user's search preferences"""
        try:
            # Get current preferences
            current_prefs = await self.get_user_preferences(user_id)

            # Update specific fields
            updated_prefs = asdict(current_prefs)
            updated_prefs.update(preferences)
            updated_prefs["updated_at"] = datetime.utcnow()

            # Save to database
            await self.database_service.save_user_preferences(user_id, updated_prefs)

            # Invalidate cache
            if self.cache_service:
                cache_key = f"{self.CACHE_PREFIX}:prefs:{user_id}"
                await self.cache_service.delete(cache_key)

            logger.info(f"⚙️ Updated preferences for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update preferences: {e}")
            raise

    # Export/Import Functionality

    async def export_user_data(self, user_id: str) -> dict[str, Any]:
        """Export all user search data"""
        try:
            # Get all search history
            all_searches = await self.get_user_search_history(
                user_id,
                limit=10000,
                filter_type=None,
            )

            # Get preferences
            preferences = await self.get_user_preferences(user_id)

            # Get analytics
            analytics = await self.get_user_analytics(user_id, days=365)

            export_data = {
                "export_date": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "search_history": [asdict(search) for search in all_searches],
                "preferences": asdict(preferences),
                "analytics": asdict(analytics),
                "metadata": {
                    "total_searches": len(all_searches),
                    "export_version": "1.0",
                },
            }

            logger.info(
                f"📤 Exported data for user {user_id}: {len(all_searches)} searches",
            )
            return export_data

        except Exception as e:
            logger.error(f"Failed to export user data: {e}")
            raise

    # Helper Methods

    async def _is_search_favorite(self, user_id: str, search_id: str) -> bool:
        """Check if search is marked as favorite"""
        try:
            return await self.database_service.is_search_favorite(user_id, search_id)
        except BaseException:
            return False

    async def _get_search_tags(self, search_id: str) -> list[str]:
        """Get tags for a search"""
        try:
            return await self.database_service.get_search_tags(search_id)
        except BaseException:
            return []

    async def _invalidate_user_caches(self, user_id: str) -> None:
        """Invalidate all caches for a user"""
        if not self.cache_service:
            return

        cache_patterns = [
            f"{self.CACHE_PREFIX}:user:{user_id}:*",
            f"{self.CACHE_PREFIX}:analytics:user:{user_id}:*",
            f"{self.CACHE_PREFIX}:prefs:{user_id}",
        ]

        for pattern in cache_patterns:
            await self.cache_service.delete_pattern(pattern)


# Factory function


async def create_search_history_service(
    database_service: PostgreSQLService,
    cache_service: RedisCacheService | None = None,
) -> SearchHistoryService:
    """Create and initialize search history service"""
    service = SearchHistoryService(database_service, cache_service)
    logger.info("✅ Search History Service created successfully")
    return service
