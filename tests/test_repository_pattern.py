#!/usr/bin/env python3
"""PAKE System - Repository Pattern Unit Tests
Comprehensive unit tests demonstrating the benefits of the Repository Pattern:
- Business logic can be tested without database dependencies
- Fast test execution with in-memory fake repositories
- Clean separation of concerns
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from ..repositories.fake_repositories import FakeUserRepository, FakeSearchHistoryRepository
from ..repositories.repository_container import FakeRepositoryContainer
from ..business.user_service import UserService
from ..domain.models import User, SearchHistory


class TestUserServiceWithFakeRepository:
    """Test UserService using fake repository for fast, isolated testing"""
    
    @pytest.fixture
    def fake_user_repository(self):
        """Create fake user repository for testing"""
        return FakeUserRepository()
    
    @pytest.fixture
    def user_service(self, fake_user_repository):
        """Create user service with fake repository"""
        return UserService(fake_user_repository)
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service):
        """Test successful user creation"""
        # Arrange
        username = "testuser"
        email = "test@example.com"
        password_hash = "hashed_password"
        full_name = "Test User"
        
        # Act
        user = await user_service.create_user(
            username=username,
            email=email,
            password_hash=password_hash,
            full_name=full_name
        )
        
        # Assert
        assert user.username == username
        assert user.email == email
        assert user.password_hash == password_hash
        assert user.full_name == full_name
        assert user.is_active is True
        assert user.is_admin is False
        assert user.id is not None
    
    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, user_service):
        """Test user creation with duplicate email"""
        # Arrange
        username1 = "user1"
        username2 = "user2"
        email = "duplicate@example.com"
        password_hash = "hashed_password"
        
        # Create first user
        await user_service.create_user(username1, email, password_hash)
        
        # Act & Assert
        with pytest.raises(ValueError, match="User with email duplicate@example.com already exists"):
            await user_service.create_user(username2, email, password_hash)
    
    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(self, user_service):
        """Test user creation with duplicate username"""
        # Arrange
        username = "duplicate_user"
        email1 = "user1@example.com"
        email2 = "user2@example.com"
        password_hash = "hashed_password"
        
        # Create first user
        await user_service.create_user(username, email1, password_hash)
        
        # Act & Assert
        with pytest.raises(ValueError, match="User with username duplicate_user already exists"):
            await user_service.create_user(username, email2, password_hash)
    
    @pytest.mark.asyncio
    async def test_create_user_invalid_email(self, user_service):
        """Test user creation with invalid email"""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid email address"):
            await user_service.create_user("testuser", "invalid-email", "password")
    
    @pytest.mark.asyncio
    async def test_create_user_short_username(self, user_service):
        """Test user creation with short username"""
        # Act & Assert
        with pytest.raises(ValueError, match="Username must be at least 3 characters long"):
            await user_service.create_user("ab", "test@example.com", "password")
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, user_service):
        """Test successful user authentication"""
        # Arrange
        username = "testuser"
        email = "test@example.com"
        password_hash = "correct_hash"
        
        user = await user_service.create_user(username, email, password_hash)
        
        # Act
        authenticated_user = await user_service.authenticate_user(email, password_hash)
        
        # Assert
        assert authenticated_user is not None
        assert authenticated_user.id == user.id
        assert authenticated_user.email == email
    
    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, user_service):
        """Test authentication with wrong password"""
        # Arrange
        username = "testuser"
        email = "test@example.com"
        password_hash = "correct_hash"
        wrong_hash = "wrong_hash"
        
        await user_service.create_user(username, email, password_hash)
        
        # Act
        authenticated_user = await user_service.authenticate_user(email, wrong_hash)
        
        # Assert
        assert authenticated_user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_inactive(self, user_service):
        """Test authentication of inactive user"""
        # Arrange
        username = "testuser"
        email = "test@example.com"
        password_hash = "correct_hash"
        
        user = await user_service.create_user(username, email, password_hash)
        await user_service.deactivate_user(user.id, "admin")
        
        # Act
        authenticated_user = await user_service.authenticate_user(email, password_hash)
        
        # Assert
        assert authenticated_user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_nonexistent(self, user_service):
        """Test authentication of nonexistent user"""
        # Act
        authenticated_user = await user_service.authenticate_user("nonexistent@example.com", "password")
        
        # Assert
        assert authenticated_user is None
    
    @pytest.mark.asyncio
    async def test_update_user_profile_success(self, user_service):
        """Test successful user profile update"""
        # Arrange
        username = "testuser"
        email = "test@example.com"
        password_hash = "password"
        
        user = await user_service.create_user(username, email, password_hash)
        
        new_full_name = "Updated Name"
        new_preferences = {"theme": "dark", "language": "en"}
        
        # Act
        updated_user = await user_service.update_user_profile(
            user.id,
            full_name=new_full_name,
            preferences=new_preferences
        )
        
        # Assert
        assert updated_user is not None
        assert updated_user.full_name == new_full_name
        assert updated_user.preferences == new_preferences
    
    @pytest.mark.asyncio
    async def test_update_user_profile_nonexistent(self, user_service):
        """Test updating profile of nonexistent user"""
        # Act & Assert
        with pytest.raises(ValueError, match="User .* not found"):
            await user_service.update_user_profile("nonexistent_id", full_name="New Name")
    
    @pytest.mark.asyncio
    async def test_deactivate_user_success(self, user_service):
        """Test successful user deactivation"""
        # Arrange
        username = "testuser"
        email = "test@example.com"
        password_hash = "password"
        
        user = await user_service.create_user(username, email, password_hash)
        
        # Act
        success = await user_service.deactivate_user(user.id, "admin")
        
        # Assert
        assert success is True
        
        # Verify user is deactivated
        deactivated_user = await user_service.get_user_by_id(user.id)
        assert deactivated_user.is_active is False
    
    @pytest.mark.asyncio
    async def test_deactivate_user_already_inactive(self, user_service):
        """Test deactivating already inactive user"""
        # Arrange
        username = "testuser"
        email = "test@example.com"
        password_hash = "password"
        
        user = await user_service.create_user(username, email, password_hash)
        await user_service.deactivate_user(user.id, "admin")
        
        # Act
        success = await user_service.deactivate_user(user.id, "admin")
        
        # Assert
        assert success is False
    
    @pytest.mark.asyncio
    async def test_deactivate_admin_user(self, user_service):
        """Test deactivating admin user (should fail)"""
        # Arrange
        username = "admin"
        email = "admin@example.com"
        password_hash = "password"
        
        user = await user_service.create_user(username, email, password_hash, is_admin=True)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Cannot deactivate admin users"):
            await user_service.deactivate_user(user.id, "admin")
    
    @pytest.mark.asyncio
    async def test_activate_user_success(self, user_service):
        """Test successful user activation"""
        # Arrange
        username = "testuser"
        email = "test@example.com"
        password_hash = "password"
        
        user = await user_service.create_user(username, email, password_hash)
        await user_service.deactivate_user(user.id, "admin")
        
        # Act
        success = await user_service.activate_user(user.id, "admin")
        
        # Assert
        assert success is True
        
        # Verify user is activated
        activated_user = await user_service.get_user_by_id(user.id)
        assert activated_user.is_active is True
    
    @pytest.mark.asyncio
    async def test_get_user_statistics(self, user_service):
        """Test user statistics calculation"""
        # Arrange
        # Create active users
        await user_service.create_user("user1", "user1@example.com", "password")
        await user_service.create_user("user2", "user2@example.com", "password")
        
        # Create admin user
        await user_service.create_user("admin", "admin@example.com", "password", is_admin=True)
        
        # Create and deactivate a user
        inactive_user = await user_service.create_user("inactive", "inactive@example.com", "password")
        await user_service.deactivate_user(inactive_user.id, "admin")
        
        # Act
        stats = await user_service.get_user_statistics()
        
        # Assert
        assert stats["total_users"] == 4
        assert stats["active_users"] == 3
        assert stats["inactive_users"] == 1
        assert stats["admin_users"] == 1
        assert stats["regular_users"] == 3
        assert stats["active_percentage"] == 75.0
    
    @pytest.mark.asyncio
    async def test_search_users(self, user_service):
        """Test user search functionality"""
        # Arrange
        await user_service.create_user("john_doe", "john@example.com", "password", full_name="John Doe")
        await user_service.create_user("jane_smith", "jane@example.com", "password", full_name="Jane Smith")
        await user_service.create_user("bob_wilson", "bob@example.com", "password", full_name="Bob Wilson")
        
        # Act
        results = await user_service.search_users("john")
        
        # Assert
        assert len(results) == 1
        assert results[0].username == "john_doe"
    
    @pytest.mark.asyncio
    async def test_search_users_by_email(self, user_service):
        """Test user search by email"""
        # Arrange
        await user_service.create_user("user1", "test@example.com", "password")
        await user_service.create_user("user2", "other@example.com", "password")
        
        # Act
        results = await user_service.search_users("test@")
        
        # Assert
        assert len(results) == 1
        assert results[0].email == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_search_users_short_query(self, user_service):
        """Test user search with short query"""
        # Act & Assert
        with pytest.raises(ValueError, match="Search query must be at least 2 characters long"):
            await user_service.search_users("a")
    
    @pytest.mark.asyncio
    async def test_health_check(self, user_service):
        """Test service health check"""
        # Act
        health = await user_service.health_check()
        
        # Assert
        assert health["status"] == "healthy"
        assert health["repository_connected"] is True
        assert health["service"] == "UserService"
        assert "user_count" in health


class TestRepositoryPatternBenefits:
    """Test demonstrating the benefits of the Repository Pattern"""
    
    @pytest.mark.asyncio
    async def test_fast_test_execution(self):
        """Test that fake repositories provide fast test execution"""
        import time
        
        # Create fake repository
        fake_repo = FakeUserRepository()
        
        # Measure time for bulk operations
        start_time = time.time()
        
        # Create many users
        for i in range(100):
            user = User(
                username=f"user{i}",
                email=f"user{i}@example.com",
                password_hash="password"
            )
            await fake_repo.create(user)
        
        # Perform searches
        for i in range(50):
            await fake_repo.get_by_email(f"user{i}@example.com")
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Assert fast execution (should be under 1 second)
        assert execution_time < 1.0
        print(f"Fake repository operations completed in {execution_time:.3f} seconds")
    
    @pytest.mark.asyncio
    async def test_isolation_from_database(self):
        """Test that business logic can be tested without database"""
        # Create fake repository
        fake_repo = FakeUserRepository()
        user_service = UserService(fake_repo)
        
        # Test business logic without any database connection
        user = await user_service.create_user("testuser", "test@example.com", "password")
        
        # Verify business logic works
        assert user.username == "testuser"
        assert user.is_active is True
        
        # Test authentication business logic
        authenticated = await user_service.authenticate_user("test@example.com", "password")
        assert authenticated is not None
        
        # Test deactivation business logic
        success = await user_service.deactivate_user(user.id, "admin")
        assert success is True
        
        # Verify user is deactivated
        deactivated_user = await user_service.get_user_by_id(user.id)
        assert deactivated_user.is_active is False
    
    @pytest.mark.asyncio
    async def test_repository_container_integration(self):
        """Test repository container with fake repositories"""
        # Create fake container
        fake_container = FakeRepositoryContainer()
        
        # Get repositories
        user_repo = fake_container.get_user_repository()
        search_repo = fake_container.get_search_history_repository()
        
        # Test repositories work
        user = User(username="test", email="test@example.com", password_hash="password")
        created_user = await user_repo.create(user)
        assert created_user.id is not None
        
        search = SearchHistory(query="test query", sources=["web"])
        created_search = await search_repo.create(search)
        assert created_search.id is not None
        
        # Test health check
        health = await fake_container.health_check()
        assert health["status"] == "healthy"
        assert health["fake_mode"] is True


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
