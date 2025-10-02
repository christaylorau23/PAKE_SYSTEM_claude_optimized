"""
Comprehensive Unit Tests for UserService

Tests all primary use cases, edge cases, and expected failure modes
for the UserService class using pytest-mock for complete isolation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt

from src.services.auth.src.services.UserService import UserService
from src.services.auth.src.services.RedisService import RedisService
from src.services.auth.src.services.TokenService import TokenService
from src.services.auth.src.services.MFAService import MFAService
from src.services.auth.src.services.SessionService import SessionService
from src.services.auth.src.services.RBACService import RBACService
from src.services.auth.src.services.PasswordService import PasswordService
from src.services.auth.src.services.EmailService import EmailService
from src.services.auth.src.types import User, UserStatus, AuthResponse
from tests.factories import UserFactory, UserInDBFactory


class TestUserServiceComprehensive:
    """Comprehensive unit tests for UserService"""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mocked dependencies for UserService"""
        return {
            'redis': AsyncMock(spec=RedisService),
            'tokenService': AsyncMock(spec=TokenService),
            'mfaService': AsyncMock(spec=MFAService),
            'sessionService': AsyncMock(spec=SessionService),
            'rbacService': AsyncMock(spec=RBACService),
            'passwordService': AsyncMock(spec=PasswordService),
            'emailService': AsyncMock(spec=EmailService),
        }

    @pytest.fixture
    def user_service(self, mock_dependencies):
        """Create UserService instance with mocked dependencies"""
        return UserService(
            redis=mock_dependencies['redis'],
            tokenService=mock_dependencies['tokenService'],
            mfaService=mock_dependencies['mfaService'],
            sessionService=mock_dependencies['sessionService'],
            rbacService=mock_dependencies['rbacService'],
            passwordService=mock_dependencies['passwordService'],
            emailService=mock_dependencies['emailService']
        )

    # ============================================================================
    # PRIMARY USE CASES - Normal Operation Paths
    # ============================================================================

    @pytest.mark.unit_functional
    async def test_create_user_success(self, user_service, mock_dependencies):
        """Test successful user creation with all valid inputs"""
        # Arrange
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'SecurePassword123!',
            'firstName': 'Test',
            'lastName': 'User',
            'roles': ['user']
        }
        
        mock_dependencies['passwordService'].hash_password.return_value = 'hashed_password'
        mock_dependencies['redis'].set.return_value = True
        mock_dependencies['emailService'].send_welcome_email.return_value = True
        
        # Act
        result = await user_service.createUser(**user_data)
        
        # Assert
        assert result is not None
        assert result.email == user_data['email']
        assert result.username == user_data['username']
        assert result.firstName == user_data['firstName']
        assert result.lastName == user_data['lastName']
        assert result.status == UserStatus.ACTIVE
        
        # Verify interactions
        mock_dependencies['passwordService'].hash_password.assert_called_once_with(user_data['password'])
        mock_dependencies['redis'].set.assert_called()
        mock_dependencies['emailService'].send_welcome_email.assert_called_once()

    @pytest.mark.unit_functional
    async def test_authenticate_user_success(self, user_service, mock_dependencies):
        """Test successful user authentication"""
        # Arrange
        username = 'testuser'
        password = 'password123'
        user_data = UserInDBFactory(username=username)
        
        mock_dependencies['redis'].get.return_value = user_data
        mock_dependencies['passwordService'].verify_password.return_value = True
        mock_dependencies['tokenService'].generateTokens.return_value = {
            'accessToken': 'access_token',
            'refreshToken': 'refresh_token',
            'tokenType': 'Bearer',
            'expiresIn': 3600
        }
        mock_dependencies['sessionService'].createSession.return_value = 'session_id'
        
        # Act
        result = await user_service.authenticateUser(username, password)
        
        # Assert
        assert result.success is True
        assert result.accessToken == 'access_token'
        assert result.refreshToken == 'refresh_token'
        assert result.user.username == username
        
        # Verify interactions
        mock_dependencies['passwordService'].verify_password.assert_called_once_with(password, user_data['hashed_password'])
        mock_dependencies['tokenService'].generateTokens.assert_called_once()
        mock_dependencies['sessionService'].createSession.assert_called_once()

    @pytest.mark.unit_functional
    async def test_get_user_by_id_success(self, user_service, mock_dependencies):
        """Test successful user retrieval by ID"""
        # Arrange
        user_id = 'user-123'
        user_data = UserInDBFactory()
        
        mock_dependencies['redis'].get.return_value = user_data
        
        # Act
        result = await user_service.getUserById(user_id)
        
        # Assert
        assert result is not None
        assert result.id == user_id
        
        # Verify interactions
        mock_dependencies['redis'].get.assert_called_once_with(f"user:{user_id}")

    @pytest.mark.unit_functional
    async def test_update_user_profile_success(self, user_service, mock_dependencies):
        """Test successful user profile update"""
        # Arrange
        user_id = 'user-123'
        update_data = {
            'firstName': 'Updated',
            'lastName': 'Name',
            'email': 'updated@example.com'
        }
        existing_user = UserInDBFactory()
        
        mock_dependencies['redis'].get.return_value = existing_user
        mock_dependencies['redis'].set.return_value = True
        
        # Act
        result = await user_service.updateUserProfile(user_id, update_data)
        
        # Assert
        assert result is not None
        assert result.firstName == update_data['firstName']
        assert result.lastName == update_data['lastName']
        assert result.email == update_data['email']
        
        # Verify interactions
        mock_dependencies['redis'].set.assert_called()

    # ============================================================================
    # EDGE CASES - Boundary Conditions and Edge Cases
    # ============================================================================

    @pytest.mark.unit_edge_case
    async def test_create_user_with_minimal_data(self, user_service, mock_dependencies):
        """Test user creation with minimal required data"""
        # Arrange
        minimal_data = {
            'email': 'minimal@example.com',
            'username': 'minimal',
            'password': 'Min123!',
            'firstName': 'Min',
            'lastName': 'User'
        }
        
        mock_dependencies['passwordService'].hash_password.return_value = 'hashed_password'
        mock_dependencies['redis'].set.return_value = True
        mock_dependencies['emailService'].send_welcome_email.return_value = True
        
        # Act
        result = await user_service.createUser(**minimal_data)
        
        # Assert
        assert result is not None
        assert result.roles == ['user']  # Default role

    @pytest.mark.unit_edge_case
    async def test_create_user_with_special_characters(self, user_service, mock_dependencies):
        """Test user creation with special characters in names"""
        # Arrange
        special_data = {
            'email': 'test@example.com',
            'username': 'user_with_underscore',
            'password': 'SecurePassword123!',
            'firstName': 'José-María',
            'lastName': "O'Connor-Smith",
            'roles': ['user']
        }
        
        mock_dependencies['passwordService'].hash_password.return_value = 'hashed_password'
        mock_dependencies['redis'].set.return_value = True
        mock_dependencies['emailService'].send_welcome_email.return_value = True
        
        # Act
        result = await user_service.createUser(**special_data)
        
        # Assert
        assert result is not None
        assert result.firstName == special_data['firstName']
        assert result.lastName == special_data['lastName']

    @pytest.mark.unit_edge_case
    async def test_authenticate_user_case_insensitive(self, user_service, mock_dependencies):
        """Test authentication with case-insensitive username"""
        # Arrange
        username = 'TestUser'
        password = 'password123'
        user_data = UserInDBFactory(username='testuser')
        
        mock_dependencies['redis'].get.return_value = user_data
        mock_dependencies['passwordService'].verify_password.return_value = True
        mock_dependencies['tokenService'].generateTokens.return_value = {
            'accessToken': 'access_token',
            'refreshToken': 'refresh_token',
            'tokenType': 'Bearer',
            'expiresIn': 3600
        }
        mock_dependencies['sessionService'].createSession.return_value = 'session_id'
        
        # Act
        result = await user_service.authenticateUser(username, password)
        
        # Assert
        assert result.success is True

    @pytest.mark.unit_edge_case
    async def test_get_user_by_nonexistent_id(self, user_service, mock_dependencies):
        """Test user retrieval with non-existent ID"""
        # Arrange
        user_id = 'nonexistent-user'
        mock_dependencies['redis'].get.return_value = None
        
        # Act
        result = await user_service.getUserById(user_id)
        
        # Assert
        assert result is None

    @pytest.mark.unit_edge_case
    async def test_update_user_with_empty_data(self, user_service, mock_dependencies):
        """Test user update with empty update data"""
        # Arrange
        user_id = 'user-123'
        existing_user = UserInDBFactory()
        
        mock_dependencies['redis'].get.return_value = existing_user
        mock_dependencies['redis'].set.return_value = True
        
        # Act
        result = await user_service.updateUserProfile(user_id, {})
        
        # Assert
        assert result is not None
        # Should return original user data unchanged
        assert result.firstName == existing_user['firstName']

    # ============================================================================
    # ERROR HANDLING - Exception Scenarios and Error Cases
    # ============================================================================

    @pytest.mark.unit_error_handling
    async def test_create_user_invalid_email(self, user_service, mock_dependencies):
        """Test user creation with invalid email format"""
        # Arrange
        invalid_data = {
            'email': 'invalid-email',
            'username': 'testuser',
            'password': 'SecurePassword123!',
            'firstName': 'Test',
            'lastName': 'User'
        }
        
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid email format"):
            await user_service.createUser(**invalid_data)

    @pytest.mark.unit_error_handling
    async def test_create_user_weak_password(self, user_service, mock_dependencies):
        """Test user creation with weak password"""
        # Arrange
        weak_password_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': '123',  # Too weak
            'firstName': 'Test',
            'lastName': 'User'
        }
        
        # Act & Assert
        with pytest.raises(ValueError, match="Password does not meet security requirements"):
            await user_service.createUser(**weak_password_data)

    @pytest.mark.unit_error_handling
    async def test_authenticate_user_wrong_password(self, user_service, mock_dependencies):
        """Test authentication with wrong password"""
        # Arrange
        username = 'testuser'
        wrong_password = 'wrongpassword'
        user_data = UserInDBFactory(username=username)
        
        mock_dependencies['redis'].get.return_value = user_data
        mock_dependencies['passwordService'].verify_password.return_value = False
        
        # Act
        result = await user_service.authenticateUser(username, wrong_password)
        
        # Assert
        assert result.success is False
        assert result.error == "Invalid credentials"

    @pytest.mark.unit_error_handling
    async def test_authenticate_user_nonexistent_user(self, user_service, mock_dependencies):
        """Test authentication with non-existent user"""
        # Arrange
        username = 'nonexistent'
        password = 'password123'
        
        mock_dependencies['redis'].get.return_value = None
        
        # Act
        result = await user_service.authenticateUser(username, password)
        
        # Assert
        assert result.success is False
        assert result.error == "User not found"

    @pytest.mark.unit_error_handling
    async def test_authenticate_user_disabled_account(self, user_service, mock_dependencies):
        """Test authentication with disabled account"""
        # Arrange
        username = 'testuser'
        password = 'password123'
        user_data = UserInDBFactory(username=username, disabled=True)
        
        mock_dependencies['redis'].get.return_value = user_data
        mock_dependencies['passwordService'].verify_password.return_value = True
        
        # Act
        result = await user_service.authenticateUser(username, password)
        
        # Assert
        assert result.success is False
        assert result.error == "Account is disabled"

    @pytest.mark.unit_error_handling
    async def test_update_user_nonexistent_user(self, user_service, mock_dependencies):
        """Test updating non-existent user"""
        # Arrange
        user_id = 'nonexistent-user'
        update_data = {'firstName': 'Updated'}
        
        mock_dependencies['redis'].get.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="User not found"):
            await user_service.updateUserProfile(user_id, update_data)

    @pytest.mark.unit_error_handling
    async def test_redis_connection_failure(self, user_service, mock_dependencies):
        """Test handling of Redis connection failures"""
        # Arrange
        user_id = 'user-123'
        mock_dependencies['redis'].get.side_effect = Exception("Redis connection failed")
        
        # Act & Assert
        with pytest.raises(Exception, match="Redis connection failed"):
            await user_service.getUserById(user_id)

    @pytest.mark.unit_error_handling
    async def test_email_service_failure(self, user_service, mock_dependencies):
        """Test handling of email service failures"""
        # Arrange
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'SecurePassword123!',
            'firstName': 'Test',
            'lastName': 'User'
        }
        
        mock_dependencies['passwordService'].hash_password.return_value = 'hashed_password'
        mock_dependencies['redis'].set.return_value = True
        mock_dependencies['emailService'].send_welcome_email.side_effect = Exception("Email service unavailable")
        
        # Act & Assert
        with pytest.raises(Exception, match="Email service unavailable"):
            await user_service.createUser(**user_data)

    # ============================================================================
    # PERFORMANCE TESTS - Algorithm Efficiency and Performance
    # ============================================================================

    @pytest.mark.unit_performance
    async def test_password_hashing_performance(self, user_service, mock_dependencies):
        """Test password hashing performance"""
        import time
        
        # Arrange
        password = 'SecurePassword123!'
        mock_dependencies['passwordService'].hash_password.return_value = 'hashed_password'
        
        # Act
        start_time = time.time()
        await user_service.createUser(
            email='test@example.com',
            username='testuser',
            password=password,
            firstName='Test',
            lastName='User'
        )
        end_time = time.time()
        
        # Assert
        execution_time = end_time - start_time
        assert execution_time < 1.0  # Should complete within 1 second
        
        # Verify password hashing was called
        mock_dependencies['passwordService'].hash_password.assert_called_once_with(password)

    @pytest.mark.unit_performance
    async def test_concurrent_user_creation(self, user_service, mock_dependencies):
        """Test concurrent user creation performance"""
        import asyncio
        
        # Arrange
        mock_dependencies['passwordService'].hash_password.return_value = 'hashed_password'
        mock_dependencies['redis'].set.return_value = True
        mock_dependencies['emailService'].send_welcome_email.return_value = True
        
        async def create_user(user_num):
            return await user_service.createUser(
                email=f'user{user_num}@example.com',
                username=f'user{user_num}',
                password='SecurePassword123!',
                firstName='Test',
                lastName='User'
            )
        
        # Act
        start_time = time.time()
        tasks = [create_user(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Assert
        assert len(results) == 10
        execution_time = end_time - start_time
        assert execution_time < 5.0  # Should complete within 5 seconds

    # ============================================================================
    # SECURITY TESTS - Authentication and Authorization
    # ============================================================================

    @pytest.mark.unit_security
    async def test_password_not_stored_in_plaintext(self, user_service, mock_dependencies):
        """Test that passwords are not stored in plaintext"""
        # Arrange
        password = 'SecurePassword123!'
        mock_dependencies['passwordService'].hash_password.return_value = 'hashed_password'
        mock_dependencies['redis'].set.return_value = True
        mock_dependencies['emailService'].send_welcome_email.return_value = True
        
        # Act
        await user_service.createUser(
            email='test@example.com',
            username='testuser',
            password=password,
            firstName='Test',
            lastName='User'
        )
        
        # Assert
        # Verify that the password was hashed before storage
        mock_dependencies['passwordService'].hash_password.assert_called_once_with(password)
        
        # Verify that the stored data doesn't contain the plaintext password
        stored_data = mock_dependencies['redis'].set.call_args[0][1]
        assert password not in str(stored_data)

    @pytest.mark.unit_security
    async def test_session_creation_on_authentication(self, user_service, mock_dependencies):
        """Test that sessions are created on successful authentication"""
        # Arrange
        username = 'testuser'
        password = 'password123'
        user_data = UserInDBFactory(username=username)
        
        mock_dependencies['redis'].get.return_value = user_data
        mock_dependencies['passwordService'].verify_password.return_value = True
        mock_dependencies['tokenService'].generateTokens.return_value = {
            'accessToken': 'access_token',
            'refreshToken': 'refresh_token',
            'tokenType': 'Bearer',
            'expiresIn': 3600
        }
        mock_dependencies['sessionService'].createSession.return_value = 'session_id'
        
        # Act
        await user_service.authenticateUser(username, password)
        
        # Assert
        mock_dependencies['sessionService'].createSession.assert_called_once()

    @pytest.mark.unit_security
    async def test_role_based_access_control(self, user_service, mock_dependencies):
        """Test role-based access control integration"""
        # Arrange
        username = 'adminuser'
        password = 'password123'
        user_data = UserInDBFactory(username=username, roles=['admin'])
        
        mock_dependencies['redis'].get.return_value = user_data
        mock_dependencies['passwordService'].verify_password.return_value = True
        mock_dependencies['tokenService'].generateTokens.return_value = {
            'accessToken': 'access_token',
            'refreshToken': 'refresh_token',
            'tokenType': 'Bearer',
            'expiresIn': 3600
        }
        mock_dependencies['sessionService'].createSession.return_value = 'session_id'
        
        # Act
        result = await user_service.authenticateUser(username, password)
        
        # Assert
        assert result.success is True
        # Verify that roles are passed to token generation
        mock_dependencies['tokenService'].generateTokens.assert_called_once()
        call_args = mock_dependencies['tokenService'].generateTokens.call_args
        assert call_args[0][0].roles == ['admin']
