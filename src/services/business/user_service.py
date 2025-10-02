#!/usr/bin/env python3
"""PAKE System - User Service with Repository Pattern
Example service layer implementation using repository pattern for clean separation
of business logic and data access concerns.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..repositories.abstract_repositories import AbstractUserRepository
from ..domain.models import User

logger = logging.getLogger(__name__)


class UserService:
    """User service with business logic separated from data access"""
    
    def __init__(self, user_repository: AbstractUserRepository):
        """Initialize user service with injected repository"""
        self.user_repository = user_repository
    
    async def create_user(
        self,
        username: str,
        email: str,
        password_hash: str,
        full_name: Optional[str] = None,
        is_admin: bool = False,
    ) -> User:
        """Create a new user with business logic validation"""
        
        # Business logic: Validate input
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters long")
        
        if not email or "@" not in email:
            raise ValueError("Invalid email address")
        
        if not password_hash:
            raise ValueError("Password hash is required")
        
        # Business logic: Check for existing users
        existing_user = await self.user_repository.get_by_email(email)
        if existing_user:
            raise ValueError(f"User with email {email} already exists")
        
        existing_user = await self.user_repository.get_by_username(username)
        if existing_user:
            raise ValueError(f"User with username {username} already exists")
        
        # Create domain model
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            is_admin=is_admin,
            is_active=True,
        )
        
        # Persist through repository
        created_user = await self.user_repository.create(user)
        
        logger.info(f"Created user: {created_user.id} ({created_user.username})")
        return created_user
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return await self.user_repository.get_by_id(user_id)
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return await self.user_repository.get_by_email(email)
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return await self.user_repository.get_by_username(username)
    
    async def authenticate_user(self, email: str, password_hash: str) -> Optional[User]:
        """Authenticate user with business logic"""
        
        user = await self.user_repository.get_by_email(email)
        if not user:
            logger.warning(f"Authentication failed: User not found for email {email}")
            return None
        
        if not user.is_active:
            logger.warning(f"Authentication failed: User {user.id} is inactive")
            return None
        
        if user.password_hash != password_hash:
            logger.warning(f"Authentication failed: Invalid password for user {user.id}")
            return None
        
        # Update last login
        await self.user_repository.update_last_login(user.id, datetime.utcnow())
        
        logger.info(f"User {user.id} authenticated successfully")
        return user
    
    async def update_user_profile(
        self,
        user_id: str,
        full_name: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> Optional[User]:
        """Update user profile with business logic"""
        
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        if not user.is_active:
            raise ValueError(f"Cannot update inactive user {user_id}")
        
        # Prepare update data
        update_data = {}
        
        if full_name is not None:
            update_data["full_name"] = full_name
        
        if preferences is not None:
            # Merge preferences with existing ones
            current_preferences = user.preferences.copy()
            current_preferences.update(preferences)
            update_data["preferences"] = current_preferences
        
        if not update_data:
            return user  # No changes to make
        
        # Update through repository
        updated_user = await self.user_repository.update(user_id, **update_data)
        
        logger.info(f"Updated user profile: {user_id}")
        return updated_user
    
    async def deactivate_user(self, user_id: str, deactivated_by: str) -> bool:
        """Deactivate user with business logic"""
        
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        if not user.is_active:
            logger.warning(f"User {user_id} is already inactive")
            return False
        
        # Business logic: Prevent deactivating admin users
        if user.is_admin:
            raise ValueError("Cannot deactivate admin users")
        
        # Deactivate through repository
        success = await self.user_repository.deactivate_user(user_id)
        
        if success:
            logger.info(f"User {user_id} deactivated by {deactivated_by}")
        
        return success
    
    async def activate_user(self, user_id: str, activated_by: str) -> bool:
        """Activate user with business logic"""
        
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        if user.is_active:
            logger.warning(f"User {user_id} is already active")
            return False
        
        # Activate through repository
        success = await self.user_repository.activate_user(user_id)
        
        if success:
            logger.info(f"User {user_id} activated by {activated_by}")
        
        return success
    
    async def get_active_users(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[User]:
        """Get all active users"""
        return await self.user_repository.get_active_users(limit=limit, offset=offset)
    
    async def get_user_count(self) -> int:
        """Get total user count"""
        return await self.user_repository.count()
    
    async def get_active_user_count(self) -> int:
        """Get active user count"""
        return await self.user_repository.count(filters={"is_active": True})
    
    async def search_users(
        self,
        query: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[User]:
        """Search users by username or email"""
        
        if not query or len(query) < 2:
            raise ValueError("Search query must be at least 2 characters long")
        
        # Get all users and filter in memory (for demo purposes)
        # In a real implementation, you might want to add search methods to the repository
        all_users = await self.user_repository.get_all(limit=1000, offset=0)
        
        query_lower = query.lower()
        matching_users = []
        
        for user in all_users:
            if (query_lower in user.username.lower() or 
                query_lower in user.email.lower() or
                (user.full_name and query_lower in user.full_name.lower())):
                matching_users.append(user)
        
        return matching_users[offset:offset + limit]
    
    async def get_user_statistics(self) -> Dict[str, Any]:
        """Get user statistics with business logic"""
        
        total_users = await self.user_repository.count()
        active_users = await self.user_repository.count(filters={"is_active": True})
        admin_users = await self.user_repository.count(filters={"is_admin": True})
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "admin_users": admin_users,
            "regular_users": total_users - admin_users,
            "active_percentage": (active_users / total_users * 100) if total_users > 0 else 0,
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on user service"""
        try:
            # Test repository connectivity
            user_count = await self.user_repository.count()
            
            return {
                "status": "healthy",
                "repository_connected": True,
                "user_count": user_count,
                "service": "UserService",
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "repository_connected": False,
                "error": str(e),
                "service": "UserService",
            }
