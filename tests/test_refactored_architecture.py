#!/usr/bin/env python3
"""PAKE System - Refactored Architecture Tests (Phase 2 Architectural Refactoring)
Comprehensive test suite for the refactored architecture components.

This test suite validates:
1. Single Responsibility Principle compliance
2. Dependency injection functionality
3. Repository pattern implementation
4. Service layer decoupling
5. Domain model purity
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from typing import Any

from ..domain.interfaces import (
    AbstractUserRepository,
    AbstractAuthenticationService,
    AbstractNotificationService,
    ServiceResult,
    ServiceStatus,
)
from ..domain.models import User, UserRole, UserStatus, create_user
from ..repositories.sqlalchemy_repositories import UserRepository
from ..business.user_service_refactored import UserService
from ..di_container import DIContainer, configure_services


class TestDomainModels:
    """Test domain model purity and immutability"""
    
    def test_user_creation(self):
        """Test user domain model creation"""
        user = create_user(
            email="test@example.com",
            hashed_password="hashed_password",
            tenant_id="tenant-123",
            first_name="John",
            last_name="Doe"
        )
        
        assert user.email == "test@example.com"
        assert user.hashed_password == "hashed_password"
        assert user.tenant_id == "tenant-123"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.full_name == "John Doe"
        assert user.role == UserRole.USER
        assert user.status == UserStatus.ACTIVE
        assert user.is_active is True
    
    def test_user_validation(self):
        """Test user domain model validation"""
        # Test invalid email
        with pytest.raises(ValueError, match="Invalid email address"):
            create_user(
                email="invalid-email",
                hashed_password="hashed_password",
                tenant_id="tenant-123"
            )
        
        # Test empty password hash
        with pytest.raises(ValueError, match="Password hash is required"):
            create_user(
                email="test@example.com",
                hashed_password="",
                tenant_id="tenant-123"
            )
        
        # Test empty tenant ID
        with pytest.raises(ValueError, match="Tenant ID is required"):
            create_user(
                email="test@example.com",
                hashed_password="hashed_password",
                tenant_id=""
            )
    
    def test_user_immutability(self):
        """Test that user domain model is immutable"""
        user = create_user(
            email="test@example.com",
            hashed_password="hashed_password",
            tenant_id="tenant-123"
        )
        
        # Attempting to modify frozen dataclass should raise error
        with pytest.raises(Exception):
            user.email = "new@example.com"


class TestRepositoryPattern:
    """Test repository pattern implementation"""
    
    @pytest.fixture
    def mock_session_maker(self):
        """Mock SQLAlchemy session maker"""
        return MagicMock()
    
    @pytest.fixture
    def user_repository(self, mock_session_maker):
        """User repository instance"""
        return UserRepository(mock_session_maker)
    
    def test_user_repository_creation(self, user_repository):
        """Test user repository creation"""
        assert user_repository is not None
        assert isinstance(user_repository, AbstractUserRepository)
    
    @pytest.mark.asyncio
    async def test_user_repository_get_by_email(self, user_repository, mock_session_maker):
        """Test getting user by email"""
        # Mock session and query result
        mock_session = AsyncMock()
        mock_session_maker.return_value.__aenter__.return_value = mock_session
        
        mock_user_orm = MagicMock()
        mock_user_orm.id = "user-123"
        mock_user_orm.email = "test@example.com"
        mock_user_orm.hashed_password = "hashed_password"
        mock_user_orm.tenant_id = "tenant-123"
        mock_user_orm.first_name = "John"
        mock_user_orm.last_name = "Doe"
        mock_user_orm.role = "user"
        mock_user_orm.status = "active"
        mock_user_orm.created_at = datetime.utcnow()
        mock_user_orm.updated_at = datetime.utcnow()
        mock_user_orm.last_login_at = None
        mock_user_orm.metadata = {}
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user_orm
        mock_session.execute.return_value = mock_result
        
        # Test the method
        user = await user_repository.get_by_email("test@example.com")
        
        assert user is not None
        assert user.email == "test@example.com"
        assert user.id == "user-123"
        assert user.tenant_id == "tenant-123"
    
    @pytest.mark.asyncio
    async def test_user_repository_get_by_email_not_found(self, user_repository, mock_session_maker):
        """Test getting user by email when not found"""
        # Mock session and query result
        mock_session = AsyncMock()
        mock_session_maker.return_value.__aenter__.return_value = mock_session
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Test the method
        user = await user_repository.get_by_email("nonexistent@example.com")
        
        assert user is None


class TestDependencyInjection:
    """Test dependency injection container"""
    
    @pytest.fixture
    def container(self):
        """DI container instance"""
        return DIContainer()
    
    def test_service_registration(self, container):
        """Test service registration"""
        container.register_singleton(AbstractUserRepository, UserRepository)
        
        assert container.is_registered(AbstractUserRepository)
        
        services = container.get_registered_services()
        assert "AbstractUserRepository" in services
        assert "UserRepository (singleton)" in services["AbstractUserRepository"]
    
    def test_service_resolution(self, container):
        """Test service resolution"""
        container.register_singleton(AbstractUserRepository, UserRepository)
        
        service = container.get(AbstractUserRepository)
        assert service is not None
        assert isinstance(service, UserRepository)
    
    def test_singleton_lifetime(self, container):
        """Test singleton service lifetime"""
        container.register_singleton(AbstractUserRepository, UserRepository)
        
        service1 = container.get(AbstractUserRepository)
        service2 = container.get(AbstractUserRepository)
        
        assert service1 is service2  # Same instance
    
    def test_transient_lifetime(self, container):
        """Test transient service lifetime"""
        container.register_transient(AbstractUserRepository, UserRepository)
        
        service1 = container.get(AbstractUserRepository)
        service2 = container.get(AbstractUserRepository)
        
        assert service1 is not service2  # Different instances
    
    def test_factory_registration(self, container):
        """Test factory registration"""
        def create_mock_repo():
            return MagicMock(spec=AbstractUserRepository)
        
        container.register_factory(AbstractUserRepository, create_mock_repo)
        
        service = container.get(AbstractUserRepository)
        assert service is not None


class TestUserService:
    """Test refactored user service"""
    
    @pytest.fixture
    def mock_user_repository(self):
        """Mock user repository"""
        return AsyncMock(spec=AbstractUserRepository)
    
    @pytest.fixture
    def mock_auth_service(self):
        """Mock authentication service"""
        return AsyncMock(spec=AbstractAuthenticationService)
    
    @pytest.fixture
    def mock_notification_service(self):
        """Mock notification service"""
        return AsyncMock(spec=AbstractNotificationService)
    
    @pytest.fixture
    def user_service(self, mock_user_repository, mock_auth_service, mock_notification_service):
        """User service instance with mocked dependencies"""
        return UserService(
            user_repository=mock_user_repository,
            auth_service=mock_auth_service,
            notification_service=mock_notification_service
        )
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service, mock_user_repository, mock_auth_service, mock_notification_service):
        """Test successful user creation"""
        # Setup mocks
        mock_auth_service.create_user.return_value = ServiceResult(
            status=ServiceStatus.SUCCESS,
            data={"hashed_password": "hashed_password"}
        )
        
        mock_user = create_user(
            email="test@example.com",
            hashed_password="hashed_password",
            tenant_id="tenant-123"
        )
        mock_user_repository.create.return_value = mock_user
        
        mock_notification_service.send_welcome_email.return_value = ServiceResult(
            status=ServiceStatus.SUCCESS,
            data=True
        )
        
        # Test user creation
        result = await user_service.create_user(
            email="test@example.com",
            password="password123",
            user_data={"tenant_id": "tenant-123"}
        )
        
        # Verify result
        assert result.status == ServiceStatus.SUCCESS
        assert result.data["email"] == "test@example.com"
        assert result.data["user_id"] == mock_user.id
        
        # Verify service calls
        mock_auth_service.create_user.assert_called_once()
        mock_user_repository.create.assert_called_once()
        mock_notification_service.send_welcome_email.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_user_validation_failure(self, user_service):
        """Test user creation with validation failure"""
        result = await user_service.create_user(
            email="invalid-email",
            password="short",
            user_data={}
        )
        
        assert result.status == ServiceStatus.FAILED
        assert "Validation failed" in result.error
    
    @pytest.mark.asyncio
    async def test_get_user_profile_success(self, user_service, mock_user_repository):
        """Test successful user profile retrieval"""
        mock_user = create_user(
            email="test@example.com",
            hashed_password="hashed_password",
            tenant_id="tenant-123",
            first_name="John",
            last_name="Doe"
        )
        mock_user_repository.get_by_id.return_value = mock_user
        
        result = await user_service.get_user_profile("user-123")
        
        assert result.status == ServiceStatus.SUCCESS
        assert result.data["email"] == "test@example.com"
        assert result.data["name"] == "John Doe"
        assert result.data["is_active"] is True
    
    @pytest.mark.asyncio
    async def test_get_user_profile_not_found(self, user_service, mock_user_repository):
        """Test user profile retrieval when user not found"""
        mock_user_repository.get_by_id.return_value = None
        
        result = await user_service.get_user_profile("nonexistent-user")
        
        assert result.status == ServiceStatus.FAILED
        assert "not found" in result.error
    
    @pytest.mark.asyncio
    async def test_get_users_by_tenant(self, user_service, mock_user_repository):
        """Test getting users by tenant"""
        mock_users = [
            create_user(
                email="user1@example.com",
                hashed_password="hashed_password",
                tenant_id="tenant-123"
            ),
            create_user(
                email="user2@example.com",
                hashed_password="hashed_password",
                tenant_id="tenant-123"
            )
        ]
        mock_user_repository.get_by_tenant.return_value = mock_users
        
        result = await user_service.get_users_by_tenant("tenant-123")
        
        assert result.status == ServiceStatus.SUCCESS
        assert len(result.data) == 2
        assert result.metadata["count"] == 2


class TestServiceIntegration:
    """Test service integration with DI container"""
    
    @pytest.mark.asyncio
    async def test_service_integration(self):
        """Test complete service integration"""
        container = DIContainer()
        configure_services(container)
        
        # Get user service from container
        user_service = container.get(UserService)
        
        assert user_service is not None
        assert isinstance(user_service, UserService)
        
        # Verify dependencies are injected
        assert user_service.user_repository is not None
        assert user_service.auth_service is not None
        assert user_service.notification_service is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
