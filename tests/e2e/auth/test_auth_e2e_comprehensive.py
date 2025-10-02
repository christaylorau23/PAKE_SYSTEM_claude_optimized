"""
Comprehensive End-to-End Tests for Authentication System

Tests complete authentication workflows from API request through service layer,
into the database, and back out to the API response using httpx client.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import httpx
import json
import jwt

from tests.factories import (
    UserFactory, UserInDBFactory, LoginRequestFactory, TokenResponseFactory,
    create_test_users, create_test_tenants
)


class TestAuthenticationE2EComprehensive:
    """Comprehensive E2E tests for authentication system"""

    @pytest.fixture
    async def auth_test_client(self):
        """Create httpx test client for authentication E2E tests"""
        async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
            yield client

    @pytest.fixture
    async def authenticated_auth_client(self, auth_test_client):
        """Create authenticated test client with valid JWT token"""
        # Register a test user
        user_data = {
            "email": "auth_e2e@example.com",
            "username": "auth_e2e_user",
            "password": "SecurePassword123!",
            "firstName": "Auth",
            "lastName": "E2E"
        }
        
        # Register user
        response = await auth_test_client.post("/auth/register", json=user_data)
        assert response.status_code == 201
        
        # Login to get token
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        
        response = await auth_test_client.post("/auth/login", json=login_data)
        assert response.status_code == 200
        
        token_data = response.json()
        access_token = token_data["access_token"]
        
        # Set authorization header
        auth_test_client.headers.update({"Authorization": f"Bearer {access_token}"})
        
        yield auth_test_client

    # ============================================================================
    # AUTHENTICATION E2E TESTS - Complete Workflows
    # ============================================================================

    @pytest.mark.e2e_user_journey
    async def test_complete_user_registration_flow(self, auth_test_client):
        """Test complete user registration flow from API to database"""
        # Arrange
        user_data = {
            "email": "complete@example.com",
            "username": "complete_user",
            "password": "SecurePassword123!",
            "firstName": "Complete",
            "lastName": "User"
        }
        
        # Act - Register user
        response = await auth_test_client.post("/auth/register", json=user_data)
        
        # Assert - Registration successful
        assert response.status_code == 201
        registration_result = response.json()
        assert registration_result["email"] == user_data["email"]
        assert registration_result["username"] == user_data["username"]
        assert registration_result["firstName"] == user_data["firstName"]
        assert registration_result["lastName"] == user_data["lastName"]
        assert "id" in registration_result
        assert "created_at" in registration_result
        
        # Verify user can be retrieved
        user_id = registration_result["id"]
        response = await auth_test_client.get(f"/auth/users/{user_id}")
        assert response.status_code == 200
        retrieved_user = response.json()
        assert retrieved_user["username"] == user_data["username"]

    @pytest.mark.e2e_user_journey
    async def test_complete_user_login_flow(self, auth_test_client):
        """Test complete user login flow from API to database"""
        # Arrange
        user_data = {
            "email": "login@example.com",
            "username": "login_user",
            "password": "SecurePassword123!",
            "firstName": "Login",
            "lastName": "User"
        }
        
        # Register user first
        response = await auth_test_client.post("/auth/register", json=user_data)
        assert response.status_code == 201
        
        # Act - Login user
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        
        response = await auth_test_client.post("/auth/login", json=login_data)
        
        # Assert - Login successful
        assert response.status_code == 200
        login_result = response.json()
        assert login_result["access_token"] is not None
        assert login_result["refresh_token"] is not None
        assert login_result["token_type"] == "Bearer"
        assert login_result["expires_in"] > 0
        assert login_result["user"]["username"] == user_data["username"]
        assert "session_id" in login_result
        
        # Verify token is valid
        access_token = login_result["access_token"]
        decoded_token = jwt.decode(access_token, options={"verify_signature": False})
        assert decoded_token["sub"] == login_result["user"]["id"]
        assert decoded_token["username"] == user_data["username"]

    @pytest.mark.e2e_user_journey
    async def test_token_refresh_flow(self, auth_test_client):
        """Test complete token refresh flow"""
        # Arrange
        user_data = {
            "email": "refresh@example.com",
            "username": "refresh_user",
            "password": "SecurePassword123!",
            "firstName": "Refresh",
            "lastName": "User"
        }
        
        # Register and login user
        response = await auth_test_client.post("/auth/register", json=user_data)
        assert response.status_code == 201
        
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        response = await auth_test_client.post("/auth/login", json=login_data)
        assert response.status_code == 200
        
        login_result = response.json()
        refresh_token = login_result["refresh_token"]
        
        # Act - Refresh token
        refresh_data = {"refresh_token": refresh_token}
        response = await auth_test_client.post("/auth/refresh", json=refresh_data)
        
        # Assert - Token refresh successful
        assert response.status_code == 200
        refresh_result = response.json()
        assert refresh_result["access_token"] is not None
        assert refresh_result["refresh_token"] is not None
        assert refresh_result["token_type"] == "Bearer"
        assert refresh_result["expires_in"] > 0
        
        # Verify new token is different from old token
        assert refresh_result["access_token"] != login_result["access_token"]
        assert refresh_result["refresh_token"] != login_result["refresh_token"]

    @pytest.mark.e2e_user_journey
    async def test_user_logout_flow(self, authenticated_auth_client):
        """Test complete user logout flow"""
        # Act - Logout user
        response = await authenticated_auth_client.post("/auth/logout")
        
        # Assert - Logout successful
        assert response.status_code == 200
        logout_result = response.json()
        assert logout_result["message"] == "Logged out successfully"
        
        # Act - Try to access protected resource after logout
        response = await authenticated_auth_client.get("/auth/profile")
        
        # Assert - Access denied after logout
        assert response.status_code == 401
        error_result = response.json()
        assert "error" in error_result

    @pytest.mark.e2e_user_journey
    async def test_password_reset_complete_flow(self, auth_test_client):
        """Test complete password reset flow"""
        # Arrange
        user_data = {
            "email": "reset@example.com",
            "username": "reset_user",
            "password": "OldPassword123!",
            "firstName": "Reset",
            "lastName": "User"
        }
        
        # Register user
        response = await auth_test_client.post("/auth/register", json=user_data)
        assert response.status_code == 201
        
        # Act - Request password reset
        reset_request = {"email": user_data["email"]}
        response = await auth_test_client.post("/auth/password-reset", json=reset_request)
        
        # Assert - Reset request successful
        assert response.status_code == 200
        reset_result = response.json()
        assert reset_result["message"] == "Password reset email sent"
        
        # Act - Confirm password reset (simulating email token)
        reset_token = "simulated_reset_token_123"
        new_password = "NewPassword123!"
        
        reset_confirm = {
            "token": reset_token,
            "new_password": new_password
        }
        response = await auth_test_client.post("/auth/password-reset/confirm", json=reset_confirm)
        
        # Assert - Reset confirmation successful
        assert response.status_code == 200
        confirm_result = response.json()
        assert confirm_result["message"] == "Password reset successfully"
        
        # Act - Login with new password
        login_data = {
            "username": user_data["username"],
            "password": new_password
        }
        response = await auth_test_client.post("/auth/login", json=login_data)
        
        # Assert - Login with new password successful
        assert response.status_code == 200
        login_result = response.json()
        assert login_result["access_token"] is not None
        
        # Act - Try to login with old password
        old_login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        response = await auth_test_client.post("/auth/login", json=old_login_data)
        
        # Assert - Login with old password fails
        assert response.status_code == 401

    @pytest.mark.e2e_user_journey
    async def test_mfa_integration_flow(self, auth_test_client):
        """Test MFA integration flow"""
        # Arrange
        user_data = {
            "email": "mfa@example.com",
            "username": "mfa_user",
            "password": "SecurePassword123!",
            "firstName": "MFA",
            "lastName": "User"
        }
        
        # Register user
        response = await auth_test_client.post("/auth/register", json=user_data)
        assert response.status_code == 201
        
        # Act - Enable MFA
        response = await auth_test_client.post("/auth/mfa/enable")
        assert response.status_code == 200
        mfa_result = response.json()
        assert "secret" in mfa_result
        assert "qr_code" in mfa_result
        
        # Act - Login with MFA
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"],
            "mfa_token": "123456"  # Simulated MFA token
        }
        response = await auth_test_client.post("/auth/login", json=login_data)
        
        # Assert - Login with MFA successful
        assert response.status_code == 200
        login_result = response.json()
        assert login_result["access_token"] is not None
        assert login_result["mfa_verified"] is True

    @pytest.mark.e2e_user_journey
    async def test_session_management_flow(self, auth_test_client):
        """Test complete session management flow"""
        # Arrange
        user_data = {
            "email": "session@example.com",
            "username": "session_user",
            "password": "SecurePassword123!",
            "firstName": "Session",
            "lastName": "User"
        }
        
        # Register user
        response = await auth_test_client.post("/auth/register", json=user_data)
        assert response.status_code == 201
        
        # Act - Login and create session
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        response = await auth_test_client.post("/auth/login", json=login_data)
        
        # Assert - Login successful
        assert response.status_code == 200
        login_result = response.json()
        session_id = login_result["session_id"]
        
        # Act - Get session info
        response = await auth_test_client.get(f"/auth/sessions/{session_id}")
        
        # Assert - Session info retrieved
        assert response.status_code == 200
        session_info = response.json()
        assert session_info["session_id"] == session_id
        assert session_info["user_id"] == login_result["user"]["id"]
        assert "created_at" in session_info
        assert "last_activity" in session_info
        
        # Act - Get all user sessions
        response = await auth_test_client.get("/auth/sessions")
        
        # Assert - Sessions retrieved
        assert response.status_code == 200
        sessions = response.json()
        assert len(sessions) > 0
        assert any(session["session_id"] == session_id for session in sessions)
        
        # Act - Logout and destroy session
        response = await auth_test_client.post("/auth/logout")
        
        # Assert - Logout successful
        assert response.status_code == 200
        
        # Act - Try to get session info after logout
        response = await auth_test_client.get(f"/auth/sessions/{session_id}")
        
        # Assert - Session not found after logout
        assert response.status_code == 404

    @pytest.mark.e2e_user_journey
    async def test_rbac_integration_flow(self, authenticated_auth_client):
        """Test RBAC integration flow"""
        # Act - Check user permissions
        response = await authenticated_auth_client.get("/auth/permissions")
        
        # Assert - Permissions retrieved
        assert response.status_code == 200
        permissions = response.json()
        assert "permissions" in permissions
        assert "roles" in permissions
        
        # Act - Check specific permission
        response = await authenticated_auth_client.get("/auth/permissions/users:read")
        
        # Assert - Permission check successful
        assert response.status_code == 200
        permission_result = response.json()
        assert "has_permission" in permission_result
        
        # Act - Get user roles
        response = await authenticated_auth_client.get("/auth/roles")
        
        # Assert - Roles retrieved
        assert response.status_code == 200
        roles = response.json()
        assert "roles" in roles
        assert len(roles["roles"]) > 0

    @pytest.mark.e2e_user_journey
    async def test_user_profile_management_flow(self, authenticated_auth_client):
        """Test complete user profile management flow"""
        # Act - Get current profile
        response = await authenticated_auth_client.get("/auth/profile")
        
        # Assert - Profile retrieved
        assert response.status_code == 200
        profile = response.json()
        assert "id" in profile
        assert "username" in profile
        assert "email" in profile
        
        # Act - Update profile
        profile_update = {
            "firstName": "Updated",
            "lastName": "Name",
            "email": "updated@example.com",
            "bio": "Updated bio information"
        }
        
        response = await authenticated_auth_client.put("/auth/profile", json=profile_update)
        
        # Assert - Profile update successful
        assert response.status_code == 200
        updated_profile = response.json()
        assert updated_profile["firstName"] == profile_update["firstName"]
        assert updated_profile["lastName"] == profile_update["lastName"]
        assert updated_profile["email"] == profile_update["email"]
        assert updated_profile["bio"] == profile_update["bio"]
        
        # Act - Get updated profile
        response = await authenticated_auth_client.get("/auth/profile")
        
        # Assert - Updated profile retrieved
        assert response.status_code == 200
        profile = response.json()
        assert profile["firstName"] == profile_update["firstName"]
        assert profile["lastName"] == profile_update["lastName"]
        assert profile["email"] == profile_update["email"]

    # ============================================================================
    # AUTHENTICATION ERROR HANDLING E2E TESTS
    # ============================================================================

    @pytest.mark.e2e_user_journey
    async def test_authentication_error_handling(self, auth_test_client):
        """Test authentication error handling and recovery"""
        # Arrange
        invalid_user_data = {
            "email": "invalid-email",
            "username": "test",
            "password": "123"
        }
        
        # Act - Try to register with invalid data
        response = await auth_test_client.post("/auth/register", json=invalid_user_data)
        
        # Assert - Registration failed with proper error
        assert response.status_code == 400
        error_result = response.json()
        assert "error" in error_result
        assert "details" in error_result
        
        # Act - Try to login with non-existent user
        login_data = {
            "username": "nonexistent_user",
            "password": "password123"
        }
        response = await auth_test_client.post("/auth/login", json=login_data)
        
        # Assert - Login failed with proper error
        assert response.status_code == 401
        error_result = response.json()
        assert "error" in error_result
        assert "message" in error_result
        
        # Act - Try to access protected resource without authentication
        response = await auth_test_client.get("/auth/profile")
        
        # Assert - Access denied with proper error
        assert response.status_code == 401
        error_result = response.json()
        assert "error" in error_result

    @pytest.mark.e2e_user_journey
    async def test_token_expiration_handling(self, auth_test_client):
        """Test token expiration handling"""
        # Arrange
        user_data = {
            "email": "expire@example.com",
            "username": "expire_user",
            "password": "SecurePassword123!",
            "firstName": "Expire",
            "lastName": "User"
        }
        
        # Register and login user
        response = await auth_test_client.post("/auth/register", json=user_data)
        assert response.status_code == 201
        
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        response = await auth_test_client.post("/auth/login", json=login_data)
        assert response.status_code == 200
        
        login_result = response.json()
        access_token = login_result["access_token"]
        
        # Set authorization header
        auth_test_client.headers.update({"Authorization": f"Bearer {access_token}"})
        
        # Act - Access protected resource
        response = await auth_test_client.get("/auth/profile")
        assert response.status_code == 200
        
        # Simulate token expiration by using invalid token
        auth_test_client.headers.update({"Authorization": "Bearer invalid_token"})
        
        # Act - Try to access protected resource with invalid token
        response = await auth_test_client.get("/auth/profile")
        
        # Assert - Access denied with proper error
        assert response.status_code == 401
        error_result = response.json()
        assert "error" in error_result

    # ============================================================================
    # AUTHENTICATION PERFORMANCE E2E TESTS
    # ============================================================================

    @pytest.mark.e2e_performance
    async def test_authentication_performance_under_load(self, auth_test_client):
        """Test authentication performance under load"""
        import time
        
        # Arrange
        user_data_list = [
            {
                "email": f"perf{i}@example.com",
                "username": f"perf_user_{i}",
                "password": "SecurePassword123!",
                "firstName": f"User{i}",
                "lastName": "Performance"
            }
            for i in range(20)
        ]
        
        # Act - Register users concurrently
        start_time = time.time()
        
        async def register_user(user_data):
            response = await auth_test_client.post("/auth/register", json=user_data)
            return response.status_code == 201
        
        tasks = [register_user(user_data) for user_data in user_data_list]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        
        # Assert
        assert all(results)  # All registrations should succeed
        execution_time = end_time - start_time
        assert execution_time < 30.0  # Should complete within 30 seconds
        
        # Act - Login users concurrently
        start_time = time.time()
        
        async def login_user(user_data):
            login_data = {
                "username": user_data["username"],
                "password": user_data["password"]
            }
            response = await auth_test_client.post("/auth/login", json=login_data)
            return response.status_code == 200
        
        tasks = [login_user(user_data) for user_data in user_data_list]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        
        # Assert
        assert all(results)  # All logins should succeed
        execution_time = end_time - start_time
        assert execution_time < 20.0  # Should complete within 20 seconds

    @pytest.mark.e2e_performance
    async def test_token_refresh_performance(self, auth_test_client):
        """Test token refresh performance"""
        import time
        
        # Arrange
        user_data = {
            "email": "refresh_perf@example.com",
            "username": "refresh_perf_user",
            "password": "SecurePassword123!",
            "firstName": "Refresh",
            "lastName": "Performance"
        }
        
        # Register and login user
        response = await auth_test_client.post("/auth/register", json=user_data)
        assert response.status_code == 201
        
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        response = await auth_test_client.post("/auth/login", json=login_data)
        assert response.status_code == 200
        
        login_result = response.json()
        refresh_token = login_result["refresh_token"]
        
        # Act - Refresh token multiple times
        start_time = time.time()
        
        async def refresh_token():
            refresh_data = {"refresh_token": refresh_token}
            response = await auth_test_client.post("/auth/refresh", json=refresh_data)
            return response.status_code == 200
        
        tasks = [refresh_token() for _ in range(50)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        
        # Assert
        assert all(results)  # All refreshes should succeed
        execution_time = end_time - start_time
        assert execution_time < 15.0  # Should complete within 15 seconds

    # ============================================================================
    # AUTHENTICATION SECURITY E2E TESTS
    # ============================================================================

    @pytest.mark.e2e_security
    async def test_password_security_validation(self, auth_test_client):
        """Test password security validation"""
        # Arrange
        weak_passwords = [
            "123",
            "password",
            "12345678",
            "Password",
            "password123",
            "PASSWORD123"
        ]
        
        for weak_password in weak_passwords:
            user_data = {
                "email": f"weak_{weak_password}@example.com",
                "username": f"weak_user_{weak_password}",
                "password": weak_password,
                "firstName": "Weak",
                "lastName": "Password"
            }
            
            # Act - Try to register with weak password
            response = await auth_test_client.post("/auth/register", json=user_data)
            
            # Assert - Registration should fail
            assert response.status_code == 400
            error_result = response.json()
            assert "error" in error_result
            assert "password" in error_result["error"].lower()

    @pytest.mark.e2e_security
    async def test_rate_limiting_protection(self, auth_test_client):
        """Test rate limiting protection"""
        # Arrange
        user_data = {
            "email": "rate@example.com",
            "username": "rate_user",
            "password": "SecurePassword123!",
            "firstName": "Rate",
            "lastName": "User"
        }
        
        # Register user
        response = await auth_test_client.post("/auth/register", json=user_data)
        assert response.status_code == 201
        
        # Act - Try to login multiple times with wrong password
        login_data = {
            "username": user_data["username"],
            "password": "wrongpassword"
        }
        
        for _ in range(10):
            response = await auth_test_client.post("/auth/login", json=login_data)
            assert response.status_code == 401
        
        # Act - Try to login with correct password after rate limiting
        correct_login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        response = await auth_test_client.post("/auth/login", json=correct_login_data)
        
        # Assert - Should be rate limited
        assert response.status_code == 429
        error_result = response.json()
        assert "error" in error_result
        assert "rate limit" in error_result["error"].lower()

    @pytest.mark.e2e_security
    async def test_session_security(self, auth_test_client):
        """Test session security"""
        # Arrange
        user_data = {
            "email": "session_sec@example.com",
            "username": "session_sec_user",
            "password": "SecurePassword123!",
            "firstName": "Session",
            "lastName": "Security"
        }
        
        # Register and login user
        response = await auth_test_client.post("/auth/register", json=user_data)
        assert response.status_code == 201
        
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        response = await auth_test_client.post("/auth/login", json=login_data)
        assert response.status_code == 200
        
        login_result = response.json()
        session_id = login_result["session_id"]
        
        # Act - Try to access session with invalid session ID
        response = await auth_test_client.get(f"/auth/sessions/invalid_session_id")
        
        # Assert - Should be denied
        assert response.status_code == 404
        
        # Act - Try to access session with valid session ID
        response = await auth_test_client.get(f"/auth/sessions/{session_id}")
        
        # Assert - Should be allowed
        assert response.status_code == 200
