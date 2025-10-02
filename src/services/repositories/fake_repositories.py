#!/usr/bin/env python3
"""PAKE System - Fake Repository Implementations
In-memory implementations of repository interfaces for unit testing.

These fake repositories store data in memory and implement the same interfaces
as the real repositories, allowing for easy unit testing without database dependencies.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

from ..domain.models import (
    SearchHistory,
    User,
)
from .abstract_repositories import (
    AbstractSearchHistoryRepository,
    AbstractUserRepository,
)

logger = logging.getLogger(__name__)


class FakeUserRepository(AbstractUserRepository):
    """Fake implementation of User repository for testing"""

    def __init__(self):
        self._users: dict[str, User] = {}
        self._next_id = 1

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self._users.get(user_id)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address"""
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[User]:
        """Get all users with optional filtering and pagination"""
        users = list(self._users.values())

        # Apply filters
        if filters:
            filtered_users = []
            for user in users:
                match = True
                for key, value in filters.items():
                    if hasattr(user, key) and getattr(user, key) != value:
                        match = False
                        break
                if match:
                    filtered_users.append(user)
            users = filtered_users

        # Apply ordering
        if order_by and hasattr(User, order_by):
            users.sort(key=lambda u: getattr(u, order_by))

        # Apply pagination
        return users[offset : offset + limit]

    async def get_active_users(self, limit: int = 100, offset: int = 0) -> list[User]:
        """Get all active users"""
        return await self.get_all(
            limit=limit, offset=offset, filters={"is_active": True}
        )

    async def create(self, user: User) -> User:
        """Create new user"""
        # Generate ID if not provided
        if not user.id:
            user.id = str(uuid4())

        # Check for duplicates
        if user.id in self._users:
            raise ValueError(f"User with ID {user.id} already exists")

        if await self.get_by_email(user.email):
            raise ValueError(f"User with email {user.email} already exists")

        if await self.get_by_username(user.username):
            raise ValueError(f"User with username {user.username} already exists")

        self._users[user.id] = user
        logger.info(f"Created fake user: {user.id}")
        return user

    async def update(self, user_id: str, **kwargs) -> Optional[User]:
        """Update user by ID"""
        user = self._users.get(user_id)
        if not user:
            return None

        # Update user attributes
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        user.updated_at = datetime.utcnow()
        logger.info(f"Updated fake user: {user_id}")
        return user

    async def update_last_login(self, user_id: str, login_time: datetime) -> bool:
        """Update user's last login time"""
        user = self._users.get(user_id)
        if not user:
            return False

        user.last_login = login_time
        user.updated_at = datetime.utcnow()
        return True

    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user account"""
        return await self.update(user_id, is_active=False) is not None

    async def activate_user(self, user_id: str) -> bool:
        """Activate user account"""
        return await self.update(user_id, is_active=True) is not None

    async def delete(self, user_id: str) -> bool:
        """Delete user by ID"""
        if user_id in self._users:
            del self._users[user_id]
            logger.info(f"Deleted fake user: {user_id}")
            return True
        return False

    async def exists(self, user_id: str) -> bool:
        """Check if user exists"""
        return user_id in self._users

    async def count(self, filters: Optional[dict[str, Any]] = None) -> int:
        """Count users matching filters"""
        users = list(self._users.values())

        if filters:
            count = 0
            for user in users:
                match = True
                for key, value in filters.items():
                    if hasattr(user, key) and getattr(user, key) != value:
                        match = False
                        break
                if match:
                    count += 1
            return count

        return len(users)

    def clear(self) -> None:
        """Clear all users (for testing)"""
        self._users.clear()
        logger.info("Cleared all fake users")


class FakeSearchHistoryRepository(AbstractSearchHistoryRepository):
    """Fake implementation of SearchHistory repository for testing"""

    def __init__(self):
        self._searches: dict[str, SearchHistory] = {}
        self._next_id = 1

    async def get_by_id(self, search_id: str) -> Optional[SearchHistory]:
        """Get search history by ID"""
        return self._searches.get(search_id)

    async def get_by_user_id(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SearchHistory]:
        """Get search history for a specific user"""
        user_searches = [
            search for search in self._searches.values() if search.user_id == user_id
        ]

        # Sort by created_at descending
        user_searches.sort(key=lambda s: s.created_at, reverse=True)

        return user_searches[offset : offset + limit]

    async def get_anonymous_searches(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SearchHistory]:
        """Get anonymous search history"""
        anonymous_searches = [
            search for search in self._searches.values() if search.user_id is None
        ]

        # Sort by created_at descending
        anonymous_searches.sort(key=lambda s: s.created_at, reverse=True)

        return anonymous_searches[offset : offset + limit]

    async def get_by_query_pattern(
        self,
        pattern: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SearchHistory]:
        """Get searches matching query pattern"""
        matching_searches = [
            search
            for search in self._searches.values()
            if pattern.lower() in search.query.lower()
        ]

        # Sort by created_at descending
        matching_searches.sort(key=lambda s: s.created_at, reverse=True)

        return matching_searches[offset : offset + limit]

    async def get_recent_searches(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> list[SearchHistory]:
        """Get recent searches within specified hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        recent_searches = [
            search
            for search in self._searches.values()
            if search.created_at >= cutoff_time
        ]

        # Sort by created_at descending
        recent_searches.sort(key=lambda s: s.created_at, reverse=True)

        return recent_searches[:limit]

    async def get_cached_searches(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SearchHistory]:
        """Get searches that resulted in cache hits"""
        cached_searches = [
            search for search in self._searches.values() if search.cache_hit
        ]

        # Sort by created_at descending
        cached_searches.sort(key=lambda s: s.created_at, reverse=True)

        return cached_searches[offset : offset + limit]

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[SearchHistory]:
        """Get all search history with optional filtering and pagination"""
        searches = list(self._searches.values())

        # Apply filters
        if filters:
            filtered_searches = []
            for search in searches:
                match = True
                for key, value in filters.items():
                    if hasattr(search, key) and getattr(search, key) != value:
                        match = False
                        break
                if match:
                    filtered_searches.append(search)
            searches = filtered_searches

        # Apply ordering
        if order_by and hasattr(SearchHistory, order_by):
            searches.sort(key=lambda s: getattr(s, order_by))
        else:
            searches.sort(key=lambda s: s.created_at, reverse=True)

        # Apply pagination
        return searches[offset : offset + limit]

    async def create(self, search_history: SearchHistory) -> SearchHistory:
        """Create new search history entry"""
        # Generate ID if not provided
        if not search_history.id:
            search_history.id = str(uuid4())

        # Check for duplicates
        if search_history.id in self._searches:
            raise ValueError(
                f"Search history with ID {search_history.id} already exists"
            )

        self._searches[search_history.id] = search_history
        logger.info(f"Created fake search history: {search_history.id}")
        return search_history

    async def update(self, search_id: str, **kwargs) -> Optional[SearchHistory]:
        """Update search history by ID"""
        search = self._searches.get(search_id)
        if not search:
            return None

        # Update search attributes
        for key, value in kwargs.items():
            if hasattr(search, key):
                setattr(search, key, value)

        logger.info(f"Updated fake search history: {search_id}")
        return search

    async def delete(self, search_id: str) -> bool:
        """Delete search history by ID"""
        if search_id in self._searches:
            del self._searches[search_id]
            logger.info(f"Deleted fake search history: {search_id}")
            return True
        return False

    async def delete_old_searches(self, days: int = 30) -> int:
        """Delete searches older than specified days"""
        cutoff_time = datetime.utcnow() - timedelta(days=days)

        old_search_ids = [
            search_id
            for search_id, search in self._searches.items()
            if search.created_at < cutoff_time
        ]

        for search_id in old_search_ids:
            del self._searches[search_id]

        logger.info(f"Deleted {len(old_search_ids)} old fake search history entries")
        return len(old_search_ids)

    async def exists(self, search_id: str) -> bool:
        """Check if search history exists"""
        return search_id in self._searches

    async def count(self, filters: Optional[dict[str, Any]] = None) -> int:
        """Count search history entries matching filters"""
        searches = list(self._searches.values())

        if filters:
            count = 0
            for search in searches:
                match = True
                for key, value in filters.items():
                    if hasattr(search, key) and getattr(search, key) != value:
                        match = False
                        break
                if match:
                    count += 1
            return count

        return len(searches)

    def clear(self) -> None:
        """Clear all search history (for testing)"""
        self._searches.clear()
        logger.info("Cleared all fake search history")


# TODO: Implement other fake repositories as needed
# class FakeSavedSearchRepository(AbstractSavedSearchRepository):
#     """Fake implementation of SavedSearch repository for testing"""
#     pass

# class FakeServiceRegistryRepository(AbstractServiceRegistryRepository):
#     """Fake implementation of ServiceRegistry repository for testing"""
#     pass

# class FakeServiceHealthCheckRepository(AbstractServiceHealthCheckRepository):
#     """Fake implementation of ServiceHealthCheck repository for testing"""
#     pass

# class FakeServiceMetricsRepository(AbstractServiceMetricsRepository):
#     """Fake implementation of ServiceMetrics repository for testing"""
#     pass

# class FakeAPIGatewayRouteRepository(AbstractAPIGatewayRouteRepository):
#     """Fake implementation of APIGatewayRoute repository for testing"""
#     pass

# class FakeSystemAlertRepository(AbstractSystemAlertRepository):
#     """Fake implementation of SystemAlert repository for testing"""
#     pass
