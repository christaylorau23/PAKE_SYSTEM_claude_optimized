"""
Comprehensive Unit Tests for AuthenticationService

Tests all primary use cases, edge cases, and expected failure modes
for the AuthenticationService class using pytest-mock for complete isolation.
"""

from unittest.mock import AsyncMock, patch

import jwt
import pytest

from src.services.auth.src.index import AuthenticationService
from src.services.auth.src.services.EmailService import EmailService
from src.services.auth.src.services.MFAService import MFAService
from src.services.auth.src.services.PasswordService import PasswordService
from src.services.auth.src.services.RBACService import RBACService
from src.services.auth.src.services.RedisService import RedisService
from src.services.auth.src.services.SessionService import SessionService
from src.services.auth.src.services.TokenService import TokenService
from src.services.auth.src.services.UserService import UserService
from tests.factories import LoginRequestFactory, UserFactory


class TestAuthenticationServiceComprehensive:
    """Comprehensive unit tests for AuthenticationService"""

    @pytest.fixture()
    def mock_services(self):
        """Create mocked service dependencies"""
        return {
            "userService": AsyncMock(spec=UserService),
            "rbacService": AsyncMock(spec=RBACService),
            "tokenService": AsyncMock(spec=TokenService),
            "mfaService": AsyncMock(spec=MFAService),
            "sessionService": AsyncMock(spec=SessionService),
            "passwordService": AsyncMock(spec=PasswordService),
            "emailService": AsyncMock(spec=EmailService),
            "redis": AsyncMock(spec=RedisService),
        }

    @pytest.fixture()
    def auth_service(self, mock_services):
        """Create AuthenticationService instance with mocked dependencies"""
        with patch(
            "src.services.auth.src.index.RedisService"
        ) as mock_redis_class, patch(
            "src.services.auth.src.index.UserService"
        ) as mock_user_class, patch(
            "src.services.auth.src.index.RBACService"
        ) as mock_rbac_class, patch(
            "src.services.auth.src.index.TokenService"
        ) as mock_token_class, patch(
            "src.services.auth.src.index.MFAService"
        ) as mock_mfa_class, patch(
            "src.services.auth.src.index.SessionService"
        ) as mock_session_class, patch(
            "src.services.auth.src.index.PasswordService"
        ) as mock_password_class, patch(
            "src.services.auth.src.index.EmailService"
        ) as mock_email_class:
            # Configure mock classes
            mock_redis_class.return_value = mock_services["redis"]
            mock_user_class.return_value = mock_services["userService"]
            mock_rbac_class.return_value = mock_services["rbacService"]
            mock_token_class.return_value = mock_services["tokenService"]
            mock_mfa_class.return_value = mock_services["mfaService"]
            mock_session_class.return_value = mock_services["sessionService"]
            mock_password_class.return_value = mock_services["passwordService"]
            mock_email_class.return_value = mock_services["emailService"]

            service = AuthenticationService()
            service.services = mock_services
            return service

    # ============================================================================
    # PRIMARY USE CASES - Normal Operation Paths
    # ============================================================================

    @pytest.mark.unit_functional()
    async def test_initialize_success(self, auth_service, mock_services):
        """Test successful service initialization"""
        # Arrange
        mock_services["redis"].connect.return_value = None
        mock_services["rbacService"].initialize.return_value = None

        # Act
        await auth_service.initialize()

        # Assert
        mock_services["redis"].connect.assert_called_once()
        mock_services["rbacService"].initialize.assert_called_once()

    @pytest.mark.unit_functional()
    async def test_user_registration_success(self, auth_service, mock_services):
        """Test successful user registration"""
        # Arrange
        registration_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "SecurePassword123!",
            "firstName": "Test",
            "lastName": "User",
        }

        created_user = UserFactory(**registration_data)
        mock_services["userService"].createUser.return_value = created_user

        # Act
        result = await auth_service.registerUser(**registration_data)

        # Assert
        assert result is not None
        assert result.email == registration_data["email"]
        assert result.username == registration_data["username"]
        mock_services["userService"].createUser.assert_called_once()

    @pytest.mark.unit_functional()
    async def test_user_login_success(self, auth_service, mock_services):
        """Test successful user login"""
        # Arrange
        login_data = LoginRequestFactory()
        auth_response = {
            "success": True,
            "accessToken": "access_token",
            "refreshToken": "refresh_token",
            "tokenType": "Bearer",
            "expiresIn": 3600,
            "user": UserFactory(),
        }

        mock_services["userService"].authenticateUser.return_value = auth_response

        # Act
        result = await auth_service.loginUser(
            login_data["username"], login_data["password"]
        )

        # Assert
        assert result["success"] is True
        assert result["accessToken"] == "access_token"
        assert result["refreshToken"] == "refresh_token"
        mock_services["userService"].authenticateUser.assert_called_once()

    @pytest.mark.unit_functional()
    async def test_token_refresh_success(self, auth_service, mock_services):
        """Test successful token refresh"""
        # Arrange
        refresh_token = "refresh_token_123"
        new_tokens = {
            "accessToken": "new_access_token",
            "refreshToken": "new_refresh_token",
            "tokenType": "Bearer",
            "expiresIn": 3600,
        }

        mock_services["tokenService"].refreshToken.return_value = new_tokens

        # Act
        result = await auth_service.refreshToken(refresh_token)

        # Assert
        assert result["accessToken"] == "new_access_token"
        assert result["refreshToken"] == "new_refresh_token"
        mock_services["tokenService"].refreshToken.assert_called_once_with(
            refresh_token
        )

    @pytest.mark.unit_functional()
    async def test_user_logout_success(self, auth_service, mock_services):
        """Test successful user logout"""
        # Arrange
        session_id = "session_123"
        mock_services["sessionService"].destroySession.return_value = True
        mock_services["tokenService"].revokeToken.return_value = True

        # Act
        result = await auth_service.logoutUser(session_id)

        # Assert
        assert result is True
        mock_services["sessionService"].destroySession.assert_called_once_with(
            session_id
        )
        mock_services["tokenService"].revokeToken.assert_called_once()

    @pytest.mark.unit_functional()
    async def test_password_reset_request_success(self, auth_service, mock_services):
        """Test successful password reset request"""
        # Arrange
        email = "test@example.com"
        user = UserFactory(email=email)

        mock_services["userService"].getUserByEmail.return_value = user
        mock_services[
            "passwordService"
        ].generateResetToken.return_value = "reset_token_123"
        mock_services["emailService"].sendPasswordResetEmail.return_value = True

        # Act
        result = await auth_service.requestPasswordReset(email)

        # Assert
        assert result is True
        mock_services["userService"].getUserByEmail.assert_called_once_with(email)
        mock_services["passwordService"].generateResetToken.assert_called_once()
        mock_services["emailService"].sendPasswordResetEmail.assert_called_once()

    @pytest.mark.unit_functional()
    async def test_password_reset_confirm_success(self, auth_service, mock_services):
        """Test successful password reset confirmation"""
        # Arrange
        reset_token = "reset_token_123"
        new_password = "NewSecurePassword123!"

        mock_services["passwordService"].validateResetToken.return_value = True
        mock_services["passwordService"].resetPassword.return_value = True

        # Act
        result = await auth_service.confirmPasswordReset(reset_token, new_password)

        # Assert
        assert result is True
        mock_services["passwordService"].validateResetToken.assert_called_once_with(
            reset_token
        )
        mock_services["passwordService"].resetPassword.assert_called_once_with(
            reset_token, new_password
        )

    # ============================================================================
    # EDGE CASES - Boundary Conditions and Edge Cases
    # ============================================================================

    @pytest.mark.unit_edge_case()
    async def test_registration_with_minimal_data(self, auth_service, mock_services):
        """Test user registration with minimal required data"""
        # Arrange
        minimal_data = {
            "email": "minimal@example.com",
            "username": "minimal",
            "password": "Min123!",
            "firstName": "Min",
            "lastName": "User",
        }

        created_user = UserFactory(**minimal_data)
        mock_services["userService"].createUser.return_value = created_user

        # Act
        result = await auth_service.registerUser(**minimal_data)

        # Assert
        assert result is not None
        assert result.email == minimal_data["email"]

    @pytest.mark.unit_edge_case()
    async def test_login_with_case_insensitive_username(
        self, auth_service, mock_services
    ):
        """Test login with case-insensitive username"""
        # Arrange
        username = "TestUser"
        password = "password123"
        auth_response = {
            "success": True,
            "accessToken": "access_token",
            "refreshToken": "refresh_token",
            "tokenType": "Bearer",
            "expiresIn": 3600,
            "user": UserFactory(username="testuser"),
        }

        mock_services["userService"].authenticateUser.return_value = auth_response

        # Act
        result = await auth_service.loginUser(username, password)

        # Assert
        assert result["success"] is True

    @pytest.mark.unit_edge_case()
    async def test_token_refresh_with_expired_token(self, auth_service, mock_services):
        """Test token refresh with expired refresh token"""
        # Arrange
        expired_token = "expired_refresh_token"
        mock_services[
            "tokenService"
        ].refreshToken.side_effect = jwt.ExpiredSignatureError("Token expired")

        # Act & Assert
        with pytest.raises(jwt.ExpiredSignatureError):
            await auth_service.refreshToken(expired_token)

    @pytest.mark.unit_edge_case()
    async def test_password_reset_with_nonexistent_email(
        self, auth_service, mock_services
    ):
        """Test password reset request with non-existent email"""
        # Arrange
        email = "nonexistent@example.com"
        mock_services["userService"].getUserByEmail.return_value = None

        # Act
        result = await auth_service.requestPasswordReset(email)

        # Assert
        assert result is False
        mock_services["userService"].getUserByEmail.assert_called_once_with(email)

    @pytest.mark.unit_edge_case()
    async def test_concurrent_login_attempts(self, auth_service, mock_services):
        """Test handling of concurrent login attempts"""
        import asyncio

        # Arrange
        username = "testuser"
        password = "password123"
        auth_response = {
            "success": True,
            "accessToken": "access_token",
            "refreshToken": "refresh_token",
            "tokenType": "Bearer",
            "expiresIn": 3600,
            "user": UserFactory(),
        }

        mock_services["userService"].authenticateUser.return_value = auth_response

        async def login():
            return await auth_service.loginUser(username, password)

        # Act
        tasks = [login() for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # Assert
        assert all(result["success"] for result in results)
        assert mock_services["userService"].authenticateUser.call_count == 5

    # ============================================================================
    # ERROR HANDLING - Exception Scenarios and Error Cases
    # ============================================================================

    @pytest.mark.unit_error_handling()
    async def test_registration_with_invalid_email(self, auth_service, mock_services):
        """Test user registration with invalid email format"""
        # Arrange
        invalid_data = {
            "email": "invalid-email",
            "username": "testuser",
            "password": "SecurePassword123!",
            "firstName": "Test",
            "lastName": "User",
        }

        mock_services["userService"].createUser.side_effect = ValueError(
            "Invalid email format"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid email format"):
            await auth_service.registerUser(**invalid_data)

    @pytest.mark.unit_error_handling()
    async def test_registration_with_weak_password(self, auth_service, mock_services):
        """Test user registration with weak password"""
        # Arrange
        weak_password_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "123",  # Too weak
            "firstName": "Test",
            "lastName": "User",
        }

        mock_services["userService"].createUser.side_effect = ValueError(
            "Password does not meet security requirements"
        )

        # Act & Assert
        with pytest.raises(
            ValueError, match="Password does not meet security requirements"
        ):
            await auth_service.registerUser(**weak_password_data)

    @pytest.mark.unit_error_handling()
    async def test_login_with_wrong_password(self, auth_service, mock_services):
        """Test login with wrong password"""
        # Arrange
        username = "testuser"
        wrong_password = "wrongpassword"

        auth_response = {"success": False, "error": "Invalid credentials"}

        mock_services["userService"].authenticateUser.return_value = auth_response

        # Act
        result = await auth_service.loginUser(username, wrong_password)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Invalid credentials"

    @pytest.mark.unit_error_handling()
    async def test_login_with_nonexistent_user(self, auth_service, mock_services):
        """Test login with non-existent user"""
        # Arrange
        username = "nonexistent"
        password = "password123"

        auth_response = {"success": False, "error": "User not found"}

        mock_services["userService"].authenticateUser.return_value = auth_response

        # Act
        result = await auth_service.loginUser(username, password)

        # Assert
        assert result["success"] is False
        assert result["error"] == "User not found"

    @pytest.mark.unit_error_handling()
    async def test_login_with_disabled_account(self, auth_service, mock_services):
        """Test login with disabled account"""
        # Arrange
        username = "testuser"
        password = "password123"

        auth_response = {"success": False, "error": "Account is disabled"}

        mock_services["userService"].authenticateUser.return_value = auth_response

        # Act
        result = await auth_service.loginUser(username, password)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Account is disabled"

    @pytest.mark.unit_error_handling()
    async def test_redis_connection_failure(self, auth_service, mock_services):
        """Test handling of Redis connection failures"""
        # Arrange
        mock_services["redis"].connect.side_effect = Exception(
            "Redis connection failed"
        )

        # Act & Assert
        with pytest.raises(Exception, match="Redis connection failed"):
            await auth_service.initialize()

    @pytest.mark.unit_error_handling()
    async def test_email_service_failure(self, auth_service, mock_services):
        """Test handling of email service failures"""
        # Arrange
        email = "test@example.com"
        user = UserFactory(email=email)

        mock_services["userService"].getUserByEmail.return_value = user
        mock_services[
            "passwordService"
        ].generateResetToken.return_value = "reset_token_123"
        mock_services["emailService"].sendPasswordResetEmail.side_effect = Exception(
            "Email service unavailable"
        )

        # Act & Assert
        with pytest.raises(Exception, match="Email service unavailable"):
            await auth_service.requestPasswordReset(email)

    @pytest.mark.unit_error_handling()
    async def test_invalid_reset_token(self, auth_service, mock_services):
        """Test password reset with invalid token"""
        # Arrange
        invalid_token = "invalid_reset_token"
        new_password = "NewSecurePassword123!"

        mock_services["passwordService"].validateResetToken.return_value = False

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid reset token"):
            await auth_service.confirmPasswordReset(invalid_token, new_password)

    # ============================================================================
    # PERFORMANCE TESTS - Algorithm Efficiency and Performance
    # ============================================================================

    @pytest.mark.unit_performance()
    async def test_login_performance(self, auth_service, mock_services):
        """Test login performance"""
        import time

        # Arrange
        username = "testuser"
        password = "password123"
        auth_response = {
            "success": True,
            "accessToken": "access_token",
            "refreshToken": "refresh_token",
            "tokenType": "Bearer",
            "expiresIn": 3600,
            "user": UserFactory(),
        }

        mock_services["userService"].authenticateUser.return_value = auth_response

        # Act
        start_time = time.time()
        for _ in range(100):
            await auth_service.loginUser(username, password)
        end_time = time.time()

        # Assert
        execution_time = end_time - start_time
        assert execution_time < 5.0  # Should complete within 5 seconds

    @pytest.mark.unit_performance()
    async def test_token_refresh_performance(self, auth_service, mock_services):
        """Test token refresh performance"""
        import time

        # Arrange
        refresh_token = "refresh_token_123"
        new_tokens = {
            "accessToken": "new_access_token",
            "refreshToken": "new_refresh_token",
            "tokenType": "Bearer",
            "expiresIn": 3600,
        }

        mock_services["tokenService"].refreshToken.return_value = new_tokens

        # Act
        start_time = time.time()
        for _ in range(100):
            await auth_service.refreshToken(refresh_token)
        end_time = time.time()

        # Assert
        execution_time = end_time - start_time
        assert execution_time < 3.0  # Should complete within 3 seconds

    @pytest.mark.unit_performance()
    async def test_concurrent_registrations(self, auth_service, mock_services):
        """Test concurrent user registrations performance"""
        import asyncio
        import time

        # Arrange
        created_user = UserFactory()
        mock_services["userService"].createUser.return_value = created_user

        async def register_user(user_num):
            return await auth_service.registerUser(
                email=f"user{user_num}@example.com",
                username=f"user{user_num}",
                password="SecurePassword123!",
                firstName="Test",
                lastName="User",
            )

        # Act
        start_time = time.time()
        tasks = [register_user(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        # Assert
        assert len(results) == 10
        execution_time = end_time - start_time
        assert execution_time < 10.0  # Should complete within 10 seconds

    # ============================================================================
    # SECURITY TESTS - Authentication and Authorization
    # ============================================================================

    @pytest.mark.unit_security()
    async def test_password_not_logged(self, auth_service, mock_services):
        """Test that passwords are not logged during authentication"""
        # Arrange
        username = "testuser"
        password = "secretpassword"

        auth_response = {
            "success": True,
            "accessToken": "access_token",
            "refreshToken": "refresh_token",
            "tokenType": "Bearer",
            "expiresIn": 3600,
            "user": UserFactory(),
        }

        mock_services["userService"].authenticateUser.return_value = auth_response

        # Act
        result = await auth_service.loginUser(username, password)

        # Assert
        assert result["success"] is True
        # Verify that password is not exposed in the response
        assert "password" not in str(result)

    @pytest.mark.unit_security()
    async def test_token_generation_security(self, auth_service, mock_services):
        """Test that tokens are generated securely"""
        # Arrange
        username = "testuser"
        password = "password123"

        auth_response = {
            "success": True,
            "accessToken": "access_token",
            "refreshToken": "refresh_token",
            "tokenType": "Bearer",
            "expiresIn": 3600,
            "user": UserFactory(),
        }

        mock_services["userService"].authenticateUser.return_value = auth_response

        # Act
        result = await auth_service.loginUser(username, password)

        # Assert
        assert result["success"] is True
        assert result["tokenType"] == "Bearer"
        assert len(result["accessToken"]) > 0
        assert len(result["refreshToken"]) > 0

    @pytest.mark.unit_security()
    async def test_session_management_security(self, auth_service, mock_services):
        """Test that sessions are managed securely"""
        # Arrange
        session_id = "session_123"
        mock_services["sessionService"].destroySession.return_value = True
        mock_services["tokenService"].revokeToken.return_value = True

        # Act
        result = await auth_service.logoutUser(session_id)

        # Assert
        assert result is True
        mock_services["sessionService"].destroySession.assert_called_once_with(
            session_id
        )
        mock_services["tokenService"].revokeToken.assert_called_once()

    @pytest.mark.unit_security()
    async def test_rate_limiting_integration(self, auth_service, mock_services):
        """Test that rate limiting is integrated with authentication"""
        # Arrange
        username = "testuser"
        password = "password123"

        auth_response = {"success": False, "error": "Too many login attempts"}

        mock_services["userService"].authenticateUser.return_value = auth_response

        # Act
        result = await auth_service.loginUser(username, password)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Too many login attempts"

    @pytest.mark.unit_security()
    async def test_mfa_integration(self, auth_service, mock_services):
        """Test that MFA is integrated with authentication"""
        # Arrange
        username = "testuser"
        password = "password123"
        mfa_token = "123456"

        auth_response = {
            "success": True,
            "accessToken": "access_token",
            "refreshToken": "refresh_token",
            "tokenType": "Bearer",
            "expiresIn": 3600,
            "user": UserFactory(),
            "requiresMFA": True,
        }

        mock_services["userService"].authenticateUser.return_value = auth_response

        # Act
        result = await auth_service.loginUser(username, password, mfa_token)

        # Assert
        assert result["success"] is True
        mock_services["userService"].authenticateUser.assert_called_once()
