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

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.business.user_service_refactored import UserService
from src.services.di_container import DIContainer, configure_services
from src.services.domain.interfaces import (
    AbstractAuthenticationService,
    AbstractNotificationService,
    AbstractUserRepository,
    ServiceResult,
    ServiceStatus,
)
from src.services.domain.models import UserRole, UserStatus, create_user
from src.services.repositories.sqlalchemy_repositories import UserRepository


class TestDomainModels:
    """Test domain model purity and immutability"""

    def test_user_creation(self) -> None:
        """Test user domain model creation"""
        user = create_user(
            email="test@example.com",
            hashed_password="hashed_password",
            tenant_id="tenant-123",
            first_name="John",
            last_name="Doe",
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

    def test_user_validation(self) -> None:
        """Test user domain model validation"""
        # Test invalid email
        with pytest.raises(ValueError, match="Invalid email address"):
            create_user(
                email="invalid-email",
                hashed_password="hashed_password",
                tenant_id="tenant-123",
            )

        # Test empty password hash
        with pytest.raises(ValueError, match="Password hash is required"):
            create_user(
                email="test@example.com", hashed_password="", tenant_id="tenant-123"
            )

        # Test empty tenant ID
        with pytest.raises(ValueError, match="Tenant ID is required"):
            create_user(
                email="test@example.com",
                hashed_password="hashed_password",
                tenant_id="",
            )

    def test_user_immutability(self) -> None:
        """Test that user domain model is immutable"""
        user = create_user(
            email="test@example.com",
            hashed_password="hashed_password",
            tenant_id="tenant-123",
        )

        # Attempting to modify frozen dataclass should raise error
        with pytest.raises(Exception):
            user.email = "new@example.com"


class TestRepositoryPattern:
    """Test repository pattern implementation"""

    @pytest.fixture
    def mock_session_maker(self) -> None:
        """Mock SQLAlchemy session maker"""
        return MagicMock()

    @pytest.fixture
    def user_repository(self) -> None:
        """User repository instance"""
        return UserRepository(mock_session_maker)

    def test_user_repository_creation(self) -> None:
        """Test user repository creation"""
        assert user_repository is not None
        assert isinstance(user_repository, AbstractUserRepository)

    @pytest.mark.asyncio
    async def test_user_repository_get_by_email(self) -> None:
        """Test getting user by email"""
        # Mock session and query result
        mock_session = AsyncMock()
        self.mock_session_maker.return_value.__aenter__.return_value = mock_session

        mock_user_orm = MagicMock()
        mock_user_orm.id = "user-123"
        mock_user_orm.email = "test@example.com"
        mock_user_orm.hashed_password = "hashed_password"
        mock_user_orm.tenant_id = "tenant-123"
        mock_user_orm.first_name = "John"
        mock_user_orm.last_name = "Doe"
        mock_user_orm.role = "user"
        mock_user_orm.status = "active"
        mock_user_orm.created_at = datetime.now(UTC)
        mock_user_orm.updated_at = datetime.now(UTC)
        mock_user_orm.last_login_at = None
        mock_user_orm.metadata = {}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user_orm
        mock_session.execute.return_value = mock_result

        # Test the method
        user = await self.user_repository.get_by_email("test@example.com")

        assert user is not None
        assert user.email == "test@example.com"
        assert user.id == "user-123"
        assert user.tenant_id == "tenant-123"

    @pytest.mark.asyncio
    async def test_user_repository_get_by_email_not_found(self) -> None:
        """Test getting user by email when not found"""
        # Mock session and query result
        mock_session = AsyncMock()
        self.mock_session_maker.return_value.__aenter__.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Test the method
        user = await self.user_repository.get_by_email("nonexistent@example.com")

        assert user is None


class TestDependencyInjection:
    """Test dependency injection container"""

    @pytest.fixture
    def container(self) -> None:
        """DI container instance"""
        return DIContainer()

    def test_service_registration(self) -> None:
        """Test service registration"""
        self.container.register_singleton(AbstractUserRepository, UserRepository)

        assert self.container.is_registered(AbstractUserRepository)

        services = self.container.get_registered_services()
        assert "AbstractUserRepository" in services
        assert "UserRepository (singleton)" in services["AbstractUserRepository"]

    def test_service_resolution(self) -> None:
        """Test service resolution"""
        self.container.register_singleton(AbstractUserRepository, UserRepository)

        service = self.container.get(AbstractUserRepository)
        assert service is not None
        assert isinstance(service, UserRepository)

    def test_singleton_lifetime(self) -> None:
        """Test singleton service lifetime"""
        self.container.register_singleton(AbstractUserRepository, UserRepository)

        service1 = self.container.get(AbstractUserRepository)
        service2 = self.container.get(AbstractUserRepository)

        assert service1 is service2  # Same instance

    def test_transient_lifetime(self) -> None:
        """Test transient service lifetime"""
        self.container.register_transient(AbstractUserRepository, UserRepository)

        service1 = self.container.get(AbstractUserRepository)
        service2 = self.container.get(AbstractUserRepository)

        assert service1 is not service2  # Different instances

    def test_factory_registration(self) -> None:
        """Test factory registration"""

        def create_mock_repo(self) -> None:
            return MagicMock(spec=AbstractUserRepository)

        self.container.register_factory(AbstractUserRepository, create_mock_repo)

        service = self.container.get(AbstractUserRepository)
        assert service is not None


class TestUserService:
    """Test refactored user service"""

    @pytest.fixture
    def mock_user_repository(self) -> None:
        """Mock user repository"""
        return AsyncMock(spec=AbstractUserRepository)

    @pytest.fixture
    def mock_auth_service(self) -> None:
        """Mock authentication service"""
        return AsyncMock(spec=AbstractAuthenticationService)

    @pytest.fixture
    def mock_notification_service(self) -> None:
        """Mock notification service"""
        return AsyncMock(spec=AbstractNotificationService)

    @pytest.fixture
    def user_service(self) -> None:
        """User service instance with mocked dependencies"""
        return UserService(
            user_repository=mock_user_repository,
            auth_service=mock_auth_service,
            notification_service=mock_notification_service,
        )

    @pytest.mark.asyncio
    async def test_create_user_success(self) -> None:
        """Test successful user creation"""
        # Setup mocks
        self.mock_auth_service.create_user.return_value = ServiceResult(
            status=ServiceStatus.SUCCESS, data={"hashed_password": "hashed_password"}
        )

        mock_user = create_user(
            email="test@example.com",
            hashed_password="hashed_password",
            tenant_id="tenant-123",
        )
        self.mock_user_repository.create.return_value = mock_user

        self.mock_notification_service.send_welcome_email.return_value = ServiceResult(
            status=ServiceStatus.SUCCESS, data=True
        )

        # Test user creation
        result = await self.user_service.create_user(
            email="test@example.com",
            password="password123",
            user_data={"tenant_id": "tenant-123"},
        )

        # Verify result
        assert result.status == ServiceStatus.SUCCESS
        assert result.data["email"] == "test@example.com"
        assert result.data["user_id"] == mock_user.id

        # Verify service calls
        self.mock_auth_service.create_user.assert_called_once()
        self.mock_user_repository.create.assert_called_once()
        self.mock_notification_service.send_welcome_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_validation_failure(self) -> None:
        """Test user creation with validation failure"""
        result = await self.user_service.create_user(
            email="invalid-email", password="short", user_data={}
        )

        assert result.status == ServiceStatus.FAILED
        assert "Validation failed" in result.error

    @pytest.mark.asyncio
    async def test_get_user_profile_success(self) -> None:
        """Test successful user profile retrieval"""
        mock_user = create_user(
            email="test@example.com",
            hashed_password="hashed_password",
            tenant_id="tenant-123",
            first_name="John",
            last_name="Doe",
        )
        self.mock_user_repository.get_by_id.return_value = mock_user

        result = await self.user_service.get_user_profile("user-123")

        assert result.status == ServiceStatus.SUCCESS
        assert result.data["email"] == "test@example.com"
        assert result.data["name"] == "John Doe"
        assert result.data["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_user_profile_not_found(self) -> None:
        """Test user profile retrieval when user not found"""
        self.mock_user_repository.get_by_id.return_value = None

        result = await self.user_service.get_user_profile("nonexistent-user")

        assert result.status == ServiceStatus.FAILED
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_get_users_by_tenant(self) -> None:
        """Test getting users by tenant"""
        mock_users = [
            create_user(
                email="user1@example.com",
                hashed_password="hashed_password",
                tenant_id="tenant-123",
            ),
            create_user(
                email="user2@example.com",
                hashed_password="hashed_password",
                tenant_id="tenant-123",
            ),
        ]
        self.mock_user_repository.get_by_tenant.return_value = mock_users

        result = await self.user_service.get_users_by_tenant("tenant-123")

        assert result.status == ServiceStatus.SUCCESS
        assert len(result.data) == 2
        assert result.metadata["count"] == 2


class TestServiceIntegration:
    """Test service integration with DI container"""

    @pytest.mark.asyncio
    async def test_service_integration(self) -> None:
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