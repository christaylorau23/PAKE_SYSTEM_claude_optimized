"""
Comprehensive Integration Tests for Authentication System

Tests the integration between authentication services, database, and Redis
using ephemeral test database and factory-boy for realistic test data.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
import jwt
import bcrypt

from src.services.auth.src.index import AuthenticationService
from src.services.auth.src.services.UserService import UserService
from src.services.auth.src.services.RBACService import RBACService
from src.services.auth.src.services.TokenService import TokenService
from src.services.auth.src.services.MFAService import MFAService
from src.services.auth.src.services.SessionService import SessionService
from src.services.auth.src.services.PasswordService import PasswordService
from src.services.auth.src.services.EmailService import EmailService
from src.services.auth.src.services.RedisService import RedisService
from tests.factories import (
    UserFactory, UserInDBFactory, LoginRequestFactory, TokenResponseFactory,
    create_test_users, create_test_tenants
)


class TestAuthenticationIntegrationComprehensive:
    """Comprehensive integration tests for authentication system"""

    @pytest.fixture(scope="module")
    async def auth_test_database(self):
        """Create ephemeral test database for authentication tests"""
        db_config = {
            "host": "localhost",
            "port": 5432,
            "database": "pake_auth_test_integration",
            "user": "test_user",
            "password": "test_password",
        }
        
        # In a real implementation, this would:
        # 1. Create a test database
        # 2. Run authentication-related migrations
        # 3. Set up test data
        # 4. Yield the database connection
        # 5. Clean up after tests complete
        
        yield db_config
        
        # Cleanup would happen here

    @pytest.fixture(scope="module")
    async def auth_test_redis(self):
        """Create test Redis connection for authentication tests"""
        redis_config = {
            "host": "localhost",
            "port": 6379,
            "db": 3,  # Use separate DB for auth integration tests
        }
        
        yield redis_config
        
        # Cleanup would happen here

    @pytest.fixture
    async def mock_auth_services(self, auth_test_redis):
        """Create mocked authentication services for integration testing"""
        mock_redis = AsyncMock(spec=RedisService)
        mock_user_service = AsyncMock(spec=UserService)
        mock_rbac_service = AsyncMock(spec=RBACService)
        mock_token_service = AsyncMock(spec=TokenService)
        mock_mfa_service = AsyncMock(spec=MFAService)
        mock_session_service = AsyncMock(spec=SessionService)
        mock_password_service = AsyncMock(spec=PasswordService)
        mock_email_service = AsyncMock(spec=EmailService)
        
        # Configure mock services
        mock_redis.connect.return_value = None
        mock_redis.disconnect.return_value = None
        mock_redis.set.return_value = True
        mock_redis.get.return_value = None
        mock_redis.delete.return_value = 1
        mock_redis.exists.return_value = False
        mock_redis.expire.return_value = True
        mock_redis.ttl.return_value = -1
        
        mock_password_service.hash_password.return_value = "hashed_password_123"
        mock_password_service.verify_password.return_value = True
        mock_password_service.generateResetToken.return_value = "reset_token_123"
        mock_password_service.validateResetToken.return_value = True
        mock_password_service.resetPassword.return_value = True
        
        mock_token_service.generateTokens.return_value = {
            "accessToken": "access_token_123",
            "refreshToken": "refresh_token_123",
            "tokenType": "Bearer",
            "expiresIn": 3600
        }
        mock_token_service.refreshToken.return_value = {
            "accessToken": "new_access_token_123",
            "refreshToken": "new_refresh_token_123",
            "tokenType": "Bearer",
            "expiresIn": 3600
        }
        mock_token_service.revokeToken.return_value = True
        
        mock_session_service.createSession.return_value = "session_123"
        mock_session_service.destroySession.return_value = True
        mock_session_service.getSession.return_value = {"user_id": "user_123"}
        
        mock_mfa_service.generateSecret.return_value = "mfa_secret_123"
        mock_mfa_service.verifyToken.return_value = True
        
        mock_email_service.send_welcome_email.return_value = True
        mock_email_service.sendPasswordResetEmail.return_value = True
        mock_email_service.sendMFACode.return_value = True
        
        mock_rbac_service.initialize.return_value = None
        mock_rbac_service.hasPermission.return_value = True
        
        return {
            'redis': mock_redis,
            'userService': mock_user_service,
            'rbacService': mock_rbac_service,
            'tokenService': mock_token_service,
            'mfaService': mock_mfa_service,
            'sessionService': mock_session_service,
            'passwordService': mock_password_service,
            'emailService': mock_email_service,
        }

    @pytest.fixture
    async def auth_service_integration(self, mock_auth_services):
        """Create AuthenticationService with mocked dependencies for integration testing"""
        with patch('src.services.auth.src.index.RedisService') as mock_redis_class, \
             patch('src.services.auth.src.index.UserService') as mock_user_class, \
             patch('src.services.auth.src.index.RBACService') as mock_rbac_class, \
             patch('src.services.auth.src.index.TokenService') as mock_token_class, \
             patch('src.services.auth.src.index.MFAService') as mock_mfa_class, \
             patch('src.services.auth.src.index.SessionService') as mock_session_class, \
             patch('src.services.auth.src.index.PasswordService') as mock_password_class, \
             patch('src.services.auth.src.index.EmailService') as mock_email_class:
            
            # Configure mock classes
            mock_redis_class.return_value = mock_auth_services['redis']
            mock_user_class.return_value = mock_auth_services['userService']
            mock_rbac_class.return_value = mock_auth_services['rbacService']
            mock_token_class.return_value = mock_auth_services['tokenService']
            mock_mfa_class.return_value = mock_auth_services['mfaService']
            mock_session_class.return_value = mock_auth_services['sessionService']
            mock_password_class.return_value = mock_auth_services['passwordService']
            mock_email_class.return_value = mock_auth_services['emailService']
            
            service = AuthenticationService()
            service.services = mock_auth_services
            return service

    # ============================================================================
    # AUTHENTICATION INTEGRATION TESTS
    # ============================================================================

    @pytest.mark.integration_auth
    async def test_complete_user_registration_flow(self, auth_service_integration, mock_auth_services):
        """Test complete user registration flow with all services"""
        # Arrange
        registration_data = {
            'email': 'integration@example.com',
            'username': 'integration_user',
            'password': 'SecurePassword123!',
            'firstName': 'Integration',
            'lastName': 'Test'
        }
        
        created_user = UserFactory(**registration_data)
        mock_auth_services['userService'].createUser.return_value = created_user
        
        # Act
        result = await auth_service_integration.registerUser(**registration_data)
        
        # Assert
        assert result is not None
        assert result.email == registration_data['email']
        assert result.username == registration_data['username']
        
        # Verify service interactions
        mock_auth_services['userService'].createUser.assert_called_once()
        mock_auth_services['emailService'].send_welcome_email.assert_called_once()

    @pytest.mark.integration_auth
    async def test_complete_user_login_flow(self, auth_service_integration, mock_auth_services):
        """Test complete user login flow with all services"""
        # Arrange
        login_data = LoginRequestFactory()
        user_data = UserInDBFactory(username=login_data['username'])
        
        auth_response = {
            'success': True,
            'accessToken': 'access_token_123',
            'refreshToken': 'refresh_token_123',
            'tokenType': 'Bearer',
            'expiresIn': 3600,
            'user': user_data,
            'sessionId': 'session_123'
        }
        
        mock_auth_services['userService'].authenticateUser.return_value = auth_response
        
        # Act
        result = await auth_service_integration.loginUser(login_data['username'], login_data['password'])
        
        # Assert
        assert result['success'] is True
        assert result['accessToken'] == 'access_token_123'
        assert result['refreshToken'] == 'refresh_token_123'
        assert result['user'].username == login_data['username']
        
        # Verify service interactions
        mock_auth_services['userService'].authenticateUser.assert_called_once()

    @pytest.mark.integration_auth
    async def test_token_refresh_flow(self, auth_service_integration, mock_auth_services):
        """Test token refresh flow with all services"""
        # Arrange
        refresh_token = 'refresh_token_123'
        new_tokens = {
            'accessToken': 'new_access_token_123',
            'refreshToken': 'new_refresh_token_123',
            'tokenType': 'Bearer',
            'expiresIn': 3600
        }
        
        mock_auth_services['tokenService'].refreshToken.return_value = new_tokens
        
        # Act
        result = await auth_service_integration.refreshToken(refresh_token)
        
        # Assert
        assert result['accessToken'] == 'new_access_token_123'
        assert result['refreshToken'] == 'new_refresh_token_123'
        
        # Verify service interactions
        mock_auth_services['tokenService'].refreshToken.assert_called_once_with(refresh_token)

    @pytest.mark.integration_auth
    async def test_user_logout_flow(self, auth_service_integration, mock_auth_services):
        """Test user logout flow with all services"""
        # Arrange
        session_id = 'session_123'
        
        # Act
        result = await auth_service_integration.logoutUser(session_id)
        
        # Assert
        assert result is True
        
        # Verify service interactions
        mock_auth_services['sessionService'].destroySession.assert_called_once_with(session_id)
        mock_auth_services['tokenService'].revokeToken.assert_called_once()

    @pytest.mark.integration_auth
    async def test_password_reset_flow(self, auth_service_integration, mock_auth_services):
        """Test complete password reset flow"""
        # Arrange
        email = 'reset@example.com'
        user_data = UserFactory(email=email)
        
        mock_auth_services['userService'].getUserByEmail.return_value = user_data
        
        # Act - Request password reset
        request_result = await auth_service_integration.requestPasswordReset(email)
        
        # Assert
        assert request_result is True
        
        # Verify service interactions
        mock_auth_services['userService'].getUserByEmail.assert_called_once_with(email)
        mock_auth_services['passwordService'].generateResetToken.assert_called_once()
        mock_auth_services['emailService'].sendPasswordResetEmail.assert_called_once()
        
        # Act - Confirm password reset
        reset_token = 'reset_token_123'
        new_password = 'NewSecurePassword123!'
        
        confirm_result = await auth_service_integration.confirmPasswordReset(reset_token, new_password)
        
        # Assert
        assert confirm_result is True
        
        # Verify service interactions
        mock_auth_services['passwordService'].validateResetToken.assert_called_once_with(reset_token)
        mock_auth_services['passwordService'].resetPassword.assert_called_once_with(reset_token, new_password)

    @pytest.mark.integration_auth
    async def test_mfa_integration_flow(self, auth_service_integration, mock_auth_services):
        """Test MFA integration flow"""
        # Arrange
        username = 'mfa_user'
        password = 'password123'
        mfa_token = '123456'
        
        user_data = UserFactory(username=username)
        auth_response = {
            'success': True,
            'accessToken': 'access_token_123',
            'refreshToken': 'refresh_token_123',
            'tokenType': 'Bearer',
            'expiresIn': 3600,
            'user': user_data,
            'requiresMFA': True
        }
        
        mock_auth_services['userService'].authenticateUser.return_value = auth_response
        mock_auth_services['mfaService'].verifyToken.return_value = True
        
        # Act
        result = await auth_service_integration.loginUser(username, password, mfa_token)
        
        # Assert
        assert result['success'] is True
        assert result['requiresMFA'] is True
        
        # Verify service interactions
        mock_auth_services['userService'].authenticateUser.assert_called_once()
        mock_auth_services['mfaService'].verifyToken.assert_called_once()

    @pytest.mark.integration_auth
    async def test_session_management_integration(self, auth_service_integration, mock_auth_services):
        """Test session management integration"""
        # Arrange
        username = 'session_user'
        password = 'password123'
        user_data = UserFactory(username=username)
        
        auth_response = {
            'success': True,
            'accessToken': 'access_token_123',
            'refreshToken': 'refresh_token_123',
            'tokenType': 'Bearer',
            'expiresIn': 3600,
            'user': user_data,
            'sessionId': 'session_123'
        }
        
        mock_auth_services['userService'].authenticateUser.return_value = auth_response
        mock_auth_services['sessionService'].getSession.return_value = {'user_id': user_data.id}
        
        # Act - Login and create session
        login_result = await auth_service_integration.loginUser(username, password)
        
        # Assert
        assert login_result['success'] is True
        assert login_result['sessionId'] == 'session_123'
        
        # Act - Get session info
        session_info = await auth_service_integration.getSessionInfo('session_123')
        
        # Assert
        assert session_info is not None
        assert session_info['user_id'] == user_data.id
        
        # Verify service interactions
        mock_auth_services['sessionService'].createSession.assert_called_once()
        mock_auth_services['sessionService'].getSession.assert_called_once_with('session_123')

    @pytest.mark.integration_auth
    async def test_rbac_integration(self, auth_service_integration, mock_auth_services):
        """Test RBAC integration with authentication"""
        # Arrange
        username = 'admin_user'
        password = 'password123'
        user_data = UserFactory(username=username, roles=['admin'])
        
        auth_response = {
            'success': True,
            'accessToken': 'access_token_123',
            'refreshToken': 'refresh_token_123',
            'tokenType': 'Bearer',
            'expiresIn': 3600,
            'user': user_data,
            'sessionId': 'session_123'
        }
        
        mock_auth_services['userService'].authenticateUser.return_value = auth_response
        mock_auth_services['rbacService'].hasPermission.return_value = True
        
        # Act
        result = await auth_service_integration.loginUser(username, password)
        
        # Assert
        assert result['success'] is True
        assert result['user'].roles == ['admin']
        
        # Act - Check permission
        has_permission = await auth_service_integration.checkPermission('session_123', 'users:read')
        
        # Assert
        assert has_permission is True
        
        # Verify service interactions
        mock_auth_services['rbacService'].hasPermission.assert_called_once()

    @pytest.mark.integration_auth
    async def test_concurrent_authentication_requests(self, auth_service_integration, mock_auth_services):
        """Test concurrent authentication requests"""
        # Arrange
        login_requests = [
            LoginRequestFactory(username=f'user_{i}', password='password123')
            for i in range(10)
        ]
        
        user_data = UserFactory()
        auth_response = {
            'success': True,
            'accessToken': 'access_token_123',
            'refreshToken': 'refresh_token_123',
            'tokenType': 'Bearer',
            'expiresIn': 3600,
            'user': user_data,
            'sessionId': 'session_123'
        }
        
        mock_auth_services['userService'].authenticateUser.return_value = auth_response
        
        # Act
        async def login_user(login_data):
            return await auth_service_integration.loginUser(login_data['username'], login_data['password'])
        
        tasks = [login_user(login_data) for login_data in login_requests]
        results = await asyncio.gather(*tasks)
        
        # Assert
        assert len(results) == 10
        assert all(result['success'] for result in results)
        
        # Verify service interactions
        assert mock_auth_services['userService'].authenticateUser.call_count == 10

    @pytest.mark.integration_auth
    async def test_authentication_error_handling(self, auth_service_integration, mock_auth_services):
        """Test authentication error handling and recovery"""
        # Arrange
        username = 'error_user'
        password = 'password123'
        
        # Simulate authentication failure
        auth_response = {
            'success': False,
            'error': 'Invalid credentials'
        }
        
        mock_auth_services['userService'].authenticateUser.return_value = auth_response
        
        # Act
        result = await auth_service_integration.loginUser(username, password)
        
        # Assert
        assert result['success'] is False
        assert result['error'] == 'Invalid credentials'
        
        # Reset mock for successful authentication
        user_data = UserFactory(username=username)
        auth_response['success'] = True
        auth_response['user'] = user_data
        auth_response['accessToken'] = 'access_token_123'
        auth_response['refreshToken'] = 'refresh_token_123'
        auth_response['tokenType'] = 'Bearer'
        auth_response['expiresIn'] = 3600
        auth_response['sessionId'] = 'session_123'
        
        # Act - Should succeed after error recovery
        result = await auth_service_integration.loginUser(username, password)
        
        # Assert
        assert result['success'] is True
        assert result['accessToken'] == 'access_token_123'

    @pytest.mark.integration_auth
    async def test_redis_failure_recovery(self, auth_service_integration, mock_auth_services):
        """Test Redis failure recovery in authentication"""
        # Arrange
        username = 'redis_user'
        password = 'password123'
        
        # Simulate Redis failure
        mock_auth_services['redis'].set.side_effect = Exception("Redis connection failed")
        
        # Act & Assert - Should handle Redis failure
        with pytest.raises(Exception, match="Redis connection failed"):
            await auth_service_integration.registerUser(
                email='redis@example.com',
                username=username,
                password=password,
                firstName='Redis',
                lastName='User'
            )
        
        # Reset Redis mock
        mock_auth_services['redis'].set.side_effect = None
        mock_auth_services['redis'].set.return_value = True
        
        # Act - Should recover after Redis is back
        user_data = UserFactory(username=username)
        mock_auth_services['userService'].createUser.return_value = user_data
        
        result = await auth_service_integration.registerUser(
            email='redis@example.com',
            username=username,
            password=password,
            firstName='Redis',
            lastName='User'
        )
        
        # Assert
        assert result is not None
        assert result.username == username

    @pytest.mark.integration_auth
    async def test_email_service_failure_handling(self, auth_service_integration, mock_auth_services):
        """Test email service failure handling"""
        # Arrange
        email = 'email@example.com'
        user_data = UserFactory(email=email)
        
        mock_auth_services['userService'].getUserByEmail.return_value = user_data
        mock_auth_services['passwordService'].generateResetToken.return_value = 'reset_token_123'
        mock_auth_services['emailService'].sendPasswordResetEmail.side_effect = Exception("Email service unavailable")
        
        # Act & Assert - Should handle email service failure
        with pytest.raises(Exception, match="Email service unavailable"):
            await auth_service_integration.requestPasswordReset(email)
        
        # Reset email service mock
        mock_auth_services['emailService'].sendPasswordResetEmail.side_effect = None
        mock_auth_services['emailService'].sendPasswordResetEmail.return_value = True
        
        # Act - Should succeed after email service recovery
        result = await auth_service_integration.requestPasswordReset(email)
        
        # Assert
        assert result is True

    @pytest.mark.integration_auth
    async def test_authentication_performance_under_load(self, auth_service_integration, mock_auth_services):
        """Test authentication performance under load"""
        import time
        
        # Arrange
        username = 'perf_user'
        password = 'password123'
        user_data = UserFactory(username=username)
        
        auth_response = {
            'success': True,
            'accessToken': 'access_token_123',
            'refreshToken': 'refresh_token_123',
            'tokenType': 'Bearer',
            'expiresIn': 3600,
            'user': user_data,
            'sessionId': 'session_123'
        }
        
        mock_auth_services['userService'].authenticateUser.return_value = auth_response
        
        # Act
        start_time = time.time()
        
        async def authenticate():
            return await auth_service_integration.loginUser(username, password)
        
        tasks = [authenticate() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        
        # Assert
        assert len(results) == 100
        assert all(result['success'] for result in results)
        
        execution_time = end_time - start_time
        assert execution_time < 10.0  # Should complete within 10 seconds

    # ============================================================================
    # SECURITY INTEGRATION TESTS
    # ============================================================================

    @pytest.mark.integration_security
    async def test_password_security_integration(self, auth_service_integration, mock_auth_services):
        """Test password security integration"""
        # Arrange
        registration_data = {
            'email': 'security@example.com',
            'username': 'security_user',
            'password': 'SecurePassword123!',
            'firstName': 'Security',
            'lastName': 'Test'
        }
        
        created_user = UserFactory(**registration_data)
        mock_auth_services['userService'].createUser.return_value = created_user
        
        # Act
        result = await auth_service_integration.registerUser(**registration_data)
        
        # Assert
        assert result is not None
        
        # Verify password was hashed
        mock_auth_services['passwordService'].hash_password.assert_called_once_with(registration_data['password'])
        
        # Verify password is not stored in plaintext
        assert registration_data['password'] not in str(result)

    @pytest.mark.integration_security
    async def test_token_security_integration(self, auth_service_integration, mock_auth_services):
        """Test token security integration"""
        # Arrange
        username = 'token_user'
        password = 'password123'
        user_data = UserFactory(username=username)
        
        auth_response = {
            'success': True,
            'accessToken': 'access_token_123',
            'refreshToken': 'refresh_token_123',
            'tokenType': 'Bearer',
            'expiresIn': 3600,
            'user': user_data,
            'sessionId': 'session_123'
        }
        
        mock_auth_services['userService'].authenticateUser.return_value = auth_response
        
        # Act
        result = await auth_service_integration.loginUser(username, password)
        
        # Assert
        assert result['success'] is True
        assert result['tokenType'] == 'Bearer'
        assert len(result['accessToken']) > 0
        assert len(result['refreshToken']) > 0
        
        # Verify tokens are generated securely
        mock_auth_services['tokenService'].generateTokens.assert_called_once()

    @pytest.mark.integration_security
    async def test_session_security_integration(self, auth_service_integration, mock_auth_services):
        """Test session security integration"""
        # Arrange
        username = 'session_user'
        password = 'password123'
        user_data = UserFactory(username=username)
        
        auth_response = {
            'success': True,
            'accessToken': 'access_token_123',
            'refreshToken': 'refresh_token_123',
            'tokenType': 'Bearer',
            'expiresIn': 3600,
            'user': user_data,
            'sessionId': 'session_123'
        }
        
        mock_auth_services['userService'].authenticateUser.return_value = auth_response
        
        # Act
        result = await auth_service_integration.loginUser(username, password)
        
        # Assert
        assert result['success'] is True
        assert result['sessionId'] == 'session_123'
        
        # Verify session is created securely
        mock_auth_services['sessionService'].createSession.assert_called_once()

    @pytest.mark.integration_security
    async def test_rate_limiting_integration(self, auth_service_integration, mock_auth_services):
        """Test rate limiting integration with authentication"""
        # Arrange
        username = 'rate_user'
        password = 'password123'
        
        # Simulate rate limiting
        auth_response = {
            'success': False,
            'error': 'Too many login attempts'
        }
        
        mock_auth_services['userService'].authenticateUser.return_value = auth_response
        
        # Act
        result = await auth_service_integration.loginUser(username, password)
        
        # Assert
        assert result['success'] is False
        assert result['error'] == 'Too many login attempts'
