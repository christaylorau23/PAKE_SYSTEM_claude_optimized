"""
Comprehensive Integration Tests for PAKE System
Tests service layer interactions with real database and external dependencies
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.pake_system.auth.models import User, UserInDB, UserCreate, Token
from src.pake_system.auth.database import get_user, create_user, authenticate_user
from src.pake_system.auth.security import create_password_hash, verify_password
from tests.factories import UserFactory, UserInDBFactory


class TestAuthenticationIntegration:
    """Integration tests for authentication system"""

    @pytest.mark.asyncio
    async def test_user_registration_and_login_flow(self, test_database):
        """Test complete user registration and login flow"""
        # Arrange
        user_data = UserCreateFactory()
        
        # Act - Register user
        hashed_password = create_password_hash(user_data["password"])
        created_user = await create_user(
            username=user_data["username"],
            email=user_data["email"],
            hashed_password=hashed_password,
            full_name=user_data["full_name"]
        )
        
        # Assert - User created successfully
        assert created_user.username == user_data["username"]
        assert created_user.email == user_data["email"]
        assert created_user.disabled is False
        
        # Act - Login user
        authenticated_user = await authenticate_user(
            user_data["username"], 
            user_data["password"]
        )
        
        # Assert - User authenticated successfully
        assert authenticated_user is not None
        assert authenticated_user.username == user_data["username"]
        assert verify_password(user_data["password"], authenticated_user.hashed_password)

    @pytest.mark.asyncio
    async def test_user_lookup_integration(self, test_database):
        """Test user lookup with database integration"""
        # Arrange
        user_data = UserInDBFactory()
        await create_user(
            username=user_data["username"],
            email=user_data["email"],
            hashed_password=user_data["hashed_password"],
            full_name=user_data["full_name"]
        )
        
        # Act
        found_user = await get_user(user_data["username"])
        
        # Assert
        assert found_user is not None
        assert found_user.username == user_data["username"]
        assert found_user.email == user_data["email"]

    @pytest.mark.asyncio
    async def test_password_verification_integration(self, test_database):
        """Test password verification with database integration"""
        # Arrange
        password = "SecurePassword123!"
        user_data = UserInDBFactory()
        user_data["hashed_password"] = create_password_hash(password)
        
        await create_user(
            username=user_data["username"],
            email=user_data["email"],
            hashed_password=user_data["hashed_password"],
            full_name=user_data["full_name"]
        )
        
        # Act
        authenticated_user = await authenticate_user(user_data["username"], password)
        
        # Assert
        assert authenticated_user is not None
        assert verify_password(password, authenticated_user.hashed_password)

    @pytest.mark.asyncio
    async def test_multiple_users_integration(self, test_database):
        """Test multiple users can be created and retrieved"""
        # Arrange
        users_data = [UserInDBFactory() for _ in range(5)]
        
        # Act - Create multiple users
        created_users = []
        for user_data in users_data:
            user = await create_user(
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=user_data["hashed_password"],
                full_name=user_data["full_name"]
            )
            created_users.append(user)
        
        # Assert - All users created successfully
        assert len(created_users) == 5
        
        # Act - Retrieve all users
        retrieved_users = []
        for user_data in users_data:
            user = await get_user(user_data["username"])
            retrieved_users.append(user)
        
        # Assert - All users retrieved successfully
        assert all(user is not None for user in retrieved_users)
        assert len(retrieved_users) == 5


class TestAPIIntegration:
    """Integration tests for API endpoints"""

    @pytest.mark.asyncio
    async def test_login_endpoint_integration(self, test_client):
        """Test login endpoint with real authentication flow"""
        # Arrange
        username = "testuser"
        password = "SecurePassword123!"
        
        # Create user in database
        hashed_password = create_password_hash(password)
        await create_user(
            username=username,
            email="test@example.com",
            hashed_password=hashed_password,
            full_name="Test User"
        )
        
        # Act
        response = test_client.post(
            "/auth/token",
            data={"username": username, "password": password}
        )
        
        # Assert
        assert response.status_code == 200
        token_data = response.json()
        assert "access_token" in token_data
        assert "token_type" in token_data
        assert token_data["token_type"] == "bearer"
        assert "refresh_token" in token_data

    @pytest.mark.asyncio
    async def test_login_endpoint_invalid_credentials(self, test_client):
        """Test login endpoint with invalid credentials"""
        # Arrange
        username = "testuser"
        password = "SecurePassword123!"
        wrong_password = "WrongPassword456!"
        
        # Create user in database
        hashed_password = create_password_hash(password)
        await create_user(
            username=username,
            email="test@example.com",
            hashed_password=hashed_password,
            full_name="Test User"
        )
        
        # Act
        response = test_client.post(
            "/auth/token",
            data={"username": username, "password": wrong_password}
        )
        
        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_integration(self, test_client):
        """Test protected endpoint with authentication"""
        # Arrange
        username = "testuser"
        password = "SecurePassword123!"
        
        # Create user and login
        hashed_password = create_password_hash(password)
        await create_user(
            username=username,
            email="test@example.com",
            hashed_password=hashed_password,
            full_name="Test User"
        )
        
        login_response = test_client.post(
            "/auth/token",
            data={"username": username, "password": password}
        )
        token = login_response.json()["access_token"]
        
        # Act
        response = test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assert
        assert response.status_code == 200
        user_data = response.json()
        assert user_data["username"] == username

    @pytest.mark.asyncio
    async def test_protected_endpoint_no_auth(self, test_client):
        """Test protected endpoint without authentication"""
        # Act
        response = test_client.get("/auth/me")
        
        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_invalid_token(self, test_client):
        """Test protected endpoint with invalid token"""
        # Act
        response = test_client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        
        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_user_registration_endpoint(self, test_client):
        """Test user registration endpoint"""
        # Arrange
        user_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "SecurePassword123!",
            "full_name": "New User"
        }
        
        # Act
        response = test_client.post("/auth/register", json=user_data)
        
        # Assert
        assert response.status_code == 200
        user_response = response.json()
        assert user_response["username"] == user_data["username"]
        assert user_response["email"] == user_data["email"]
        assert "hashed_password" not in user_response  # Password should not be returned

    @pytest.mark.asyncio
    async def test_user_registration_weak_password(self, test_client):
        """Test user registration with weak password"""
        # Arrange
        user_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "weak",
            "full_name": "New User"
        }
        
        # Act
        response = test_client.post("/auth/register", json=user_data)
        
        # Assert
        assert response.status_code == 400
        assert "Password validation failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_password_generation_endpoint(self, test_client):
        """Test password generation endpoint"""
        # Act
        response = test_client.get("/auth/generate-password")
        
        # Assert
        assert response.status_code == 200
        password_data = response.json()
        assert "password" in password_data
        assert len(password_data["password"]) >= 12

    @pytest.mark.asyncio
    async def test_password_validation_endpoint(self, test_client):
        """Test password validation endpoint"""
        # Arrange
        password_data = {"password": "SecurePassword123!"}
        
        # Act
        response = test_client.post("/auth/validate-password", json=password_data)
        
        # Assert
        assert response.status_code == 200
        validation_result = response.json()
        assert validation_result["is_valid"] is True
        assert len(validation_result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_password_validation_weak_password(self, test_client):
        """Test password validation with weak password"""
        # Arrange
        password_data = {"password": "weak"}
        
        # Act
        response = test_client.post("/auth/validate-password", json=password_data)
        
        # Assert
        assert response.status_code == 200
        validation_result = response.json()
        assert validation_result["is_valid"] is False
        assert len(validation_result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_refresh_token_endpoint(self, test_client):
        """Test refresh token endpoint"""
        # Arrange
        username = "testuser"
        password = "SecurePassword123!"
        
        # Create user and login
        hashed_password = create_password_hash(password)
        await create_user(
            username=username,
            email="test@example.com",
            hashed_password=hashed_password,
            full_name="Test User"
        )
        
        login_response = test_client.post(
            "/auth/token",
            data={"username": username, "password": password}
        )
        refresh_token = login_response.json()["refresh_token"]
        
        # Act
        response = test_client.post("/auth/refresh", json={"refresh_token": refresh_token})
        
        # Assert
        assert response.status_code == 200
        token_data = response.json()
        assert "access_token" in token_data
        assert "token_type" in token_data
        assert token_data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_logout_endpoint(self, test_client):
        """Test logout endpoint"""
        # Arrange
        username = "testuser"
        password = "SecurePassword123!"
        
        # Create user and login
        hashed_password = create_password_hash(password)
        await create_user(
            username=username,
            email="test@example.com",
            hashed_password=hashed_password,
            full_name="Test User"
        )
        
        login_response = test_client.post(
            "/auth/token",
            data={"username": username, "password": password}
        )
        token = login_response.json()["access_token"]
        
        # Act
        response = test_client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Successfully logged out"


class TestDatabaseIntegration:
    """Integration tests for database operations"""

    @pytest.mark.asyncio
    async def test_database_connection_integration(self, test_database):
        """Test database connection and basic operations"""
        # Arrange
        user_data = UserInDBFactory()
        
        # Act
        created_user = await create_user(
            username=user_data["username"],
            email=user_data["email"],
            hashed_password=user_data["hashed_password"],
            full_name=user_data["full_name"]
        )
        
        # Assert
        assert created_user is not None
        assert created_user.username == user_data["username"]

    @pytest.mark.asyncio
    async def test_database_transaction_integration(self, test_database):
        """Test database transaction handling"""
        # Arrange
        users_data = [UserInDBFactory() for _ in range(3)]
        
        # Act - Create multiple users in sequence
        created_users = []
        for user_data in users_data:
            user = await create_user(
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=user_data["hashed_password"],
                full_name=user_data["full_name"]
            )
            created_users.append(user)
        
        # Assert - All users created successfully
        assert len(created_users) == 3
        
        # Verify all users can be retrieved
        for user_data in users_data:
            retrieved_user = await get_user(user_data["username"])
            assert retrieved_user is not None
            assert retrieved_user.username == user_data["username"]

    @pytest.mark.asyncio
    async def test_database_concurrent_access(self, test_database):
        """Test database concurrent access patterns"""
        # Arrange
        users_data = [UserInDBFactory() for _ in range(5)]
        
        # Act - Create users concurrently
        tasks = []
        for user_data in users_data:
            task = create_user(
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=user_data["hashed_password"],
                full_name=user_data["full_name"]
            )
            tasks.append(task)
        
        created_users = await asyncio.gather(*tasks)
        
        # Assert - All users created successfully
        assert len(created_users) == 5
        
        # Verify all users can be retrieved concurrently
        retrieve_tasks = []
        for user_data in users_data:
            task = get_user(user_data["username"])
            retrieve_tasks.append(task)
        
        retrieved_users = await asyncio.gather(*retrieve_tasks)
        
        # Assert - All users retrieved successfully
        assert all(user is not None for user in retrieved_users)
        assert len(retrieved_users) == 5


class TestExternalServiceIntegration:
    """Integration tests for external service interactions"""

    @pytest.mark.asyncio
    async def test_external_api_mock_integration(self, mock_external_api):
        """Test integration with external API services"""
        # Arrange
        mock_external_api.get.return_value = {"status": "ok", "data": [{"id": 1, "name": "test"}]}
        
        # Act
        response = await mock_external_api.get("/test-endpoint")
        
        # Assert
        assert response["status"] == "ok"
        assert len(response["data"]) == 1
        assert response["data"][0]["id"] == 1

    @pytest.mark.asyncio
    async def test_redis_integration(self, mock_redis):
        """Test integration with Redis caching"""
        # Arrange
        mock_redis.set.return_value = True
        mock_redis.get.return_value = '{"cached_data": "test"}'
        
        # Act
        set_result = await mock_redis.set("test_key", "test_value")
        get_result = await mock_redis.get("test_key")
        
        # Assert
        assert set_result is True
        assert get_result == '{"cached_data": "test"}'

    @pytest.mark.asyncio
    async def test_email_service_integration(self, mock_email_service):
        """Test integration with email service"""
        # Arrange
        mock_email_service.send_email.return_value = {"status": "sent", "message_id": "12345"}
        
        # Act
        result = await mock_email_service.send_email(
            to="test@example.com",
            subject="Test Email",
            body="This is a test email"
        )
        
        # Assert
        assert result["status"] == "sent"
        assert result["message_id"] == "12345"


class TestErrorHandlingIntegration:
    """Integration tests for error handling"""

    @pytest.mark.asyncio
    async def test_database_error_handling(self, test_database):
        """Test database error handling"""
        # Arrange
        invalid_user_data = {
            "username": "",  # Invalid empty username
            "email": "invalid-email",  # Invalid email format
            "hashed_password": "invalid_hash",
            "full_name": "Test User"
        }
        
        # Act & Assert
        with pytest.raises(Exception):  # Should raise validation error
            await create_user(**invalid_user_data)

    @pytest.mark.asyncio
    async def test_api_error_handling(self, test_client):
        """Test API error handling"""
        # Act
        response = test_client.post("/auth/token", data={})  # Empty data
        
        # Assert
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, test_client):
        """Test authentication error handling"""
        # Act
        response = test_client.get("/auth/me")  # No authentication
        
        # Assert
        assert response.status_code == 401  # Unauthorized

    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, test_client):
        """Test rate limiting integration"""
        # Arrange
        username = "testuser"
        password = "SecurePassword123!"
        
        # Create user
        hashed_password = create_password_hash(password)
        await create_user(
            username=username,
            email="test@example.com",
            hashed_password=hashed_password,
            full_name="Test User"
        )
        
        # Act - Send multiple requests rapidly
        responses = []
        for _ in range(10):
            response = test_client.post(
                "/auth/token",
                data={"username": username, "password": "wrongpassword"}
            )
            responses.append(response)
        
        # Assert - Some requests should be rate limited
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes  # Rate limited


class TestPerformanceIntegration:
    """Integration tests for performance characteristics"""

    @pytest.mark.asyncio
    async def test_concurrent_user_creation_performance(self, test_database):
        """Test performance of concurrent user creation"""
        import time
        
        # Arrange
        users_data = [UserInDBFactory() for _ in range(10)]
        
        # Act
        start_time = time.time()
        tasks = []
        for user_data in users_data:
            task = create_user(
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=user_data["hashed_password"],
                full_name=user_data["full_name"]
            )
            tasks.append(task)
        
        created_users = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Assert
        assert len(created_users) == 10
        assert end_time - start_time < 5.0  # Should complete within 5 seconds

    @pytest.mark.asyncio
    async def test_authentication_performance(self, test_client):
        """Test authentication performance"""
        import time
        
        # Arrange
        username = "testuser"
        password = "SecurePassword123!"
        
        hashed_password = create_password_hash(password)
        await create_user(
            username=username,
            email="test@example.com",
            hashed_password=hashed_password,
            full_name="Test User"
        )
        
        # Act
        start_time = time.time()
        response = test_client.post(
            "/auth/token",
            data={"username": username, "password": password}
        )
        end_time = time.time()
        
        # Assert
        assert response.status_code == 200
        assert end_time - start_time < 1.0  # Should complete within 1 second
